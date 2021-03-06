import json
import numpy as np
import tensorflow as tf
import math
from inputs import get_filename_list, dataset_inputs
from utils import per_class_acc, fast_hist, get_hist, print_hist_summary


def vgg_param_load(vgg16_npy_path):
    vgg_param_dict = np.load(vgg16_npy_path, encoding='latin1').item()
    print("vgg parameter loaded")
    return vgg_param_dict


with open("config.json") as f:
    config = json.load(f)
vgg_param_dict = vgg_param_load(config["VGG_FILE"])


def inference(images, labels, training_state):
    """
    images: is the input images, Training data also Test data
    labels: corresponding labels for images
    batch_size
    phase_train: is utilized to notify if the parameter should keep as a constant or keep updating 
    """
    # Before enter the images into the architecture, we need to do Local Contrast Normalization
    # But it seems a bit complicated, so we use Local Response Normalization which is implemented in Tensorflow
    # Reference page:https://www.tensorflow.org/api_docs/python/tf/nn/local_response_normalization
    norm1 = tf.nn.lrn(images, depth_radius=5, bias=1.0, alpha=0.0001, beta=0.75, name='norm1')
    # first box of convolution layer,each part we do convolution two times, so we have conv1_1, and conv1_2
    conv1_1 = conv_layer_enc(norm1, "conv1_1", [3, 3, 3, 64], training_state)
    conv1_2 = conv_layer_enc(conv1_1, "conv1_2", [3, 3, 64, 64], training_state)
    pool1, pool1_index, shape_1 = max_pool(conv1_2, 'pool1')

    # Second box of covolution layer(4)
    conv2_1 = conv_layer_enc(pool1, "conv2_1", [3, 3, 64, 128], training_state)
    conv2_2 = conv_layer_enc(conv2_1, "conv2_2", [3, 3, 128, 128], training_state)
    pool2, pool2_index, shape_2 = max_pool(conv2_2, 'pool2')

    # Third box of covolution layer(7)
    conv3_1 = conv_layer_enc(pool2, "conv3_1", [3, 3, 128, 256], training_state)
    conv3_2 = conv_layer_enc(conv3_1, "conv3_2", [3, 3, 256, 256], training_state)
    conv3_3 = conv_layer_enc(conv3_2, "conv3_3", [3, 3, 256, 256], training_state)
    pool3, pool3_index, shape_3 = max_pool(conv3_3, 'pool3')

    # Fourth box of covolution layer(10)
    conv4_1 = conv_layer_enc(pool3, "conv4_1", [3, 3, 256, 512], training_state)
    conv4_2 = conv_layer_enc(conv4_1, "conv4_2", [3, 3, 512, 512], training_state)
    conv4_3 = conv_layer_enc(conv4_2, "conv4_3", [3, 3, 512, 512], training_state)
    pool4, pool4_index, shape_4 = max_pool(conv4_3, 'pool4')

    # Fifth box of covolution layers(13)
    conv5_1 = conv_layer_enc(pool4, "conv5_1", [3, 3, 512, 512], training_state)
    conv5_2 = conv_layer_enc(conv5_1, "conv5_2", [3, 3, 512, 512], training_state)
    conv5_3 = conv_layer_enc(conv5_2, "conv5_3", [3, 3, 512, 512], training_state)
    pool5, pool5_index, shape_5 = max_pool(conv5_3, 'pool5')

    # ---------------------So Now the encoder process has been Finished--------------------------------------#
    # ------------------Then Let's start Decoder Process-----------------------------------------------------#

    # First box of decovolution layers(3)
    deconv5_1 = up_sampling(pool5, pool5_index, shape_5, name="unpool_5")
    # deconv1_2 = deconv_layer(deconv1_1,[3,3,512,512],shape_5,"deconv1_2",training_state)
    # deconv1_3 = deconv_layer(deconv1_2,[3,3,512,512],shape_5,"deconv1_3",training_state)
    # deconv1_4 = deconv_layer(deconv1_3,[3,3,512,512],shape_5,"deconv1_4",training_state)
    deconv5_2 = conv_layer(deconv5_1, "deconv5_2", [3, 3, 512, 512], training_state)
    deconv5_3 = conv_layer(deconv5_2, "deconv5_3", [3, 3, 512, 512], training_state)
    deconv5_4 = conv_layer(deconv5_3, "deconv5_4", [3, 3, 512, 512], training_state)
    # Second box of deconvolution layers(6)
    deconv4_1 = up_sampling(deconv5_4, pool4_index, shape_4, name="unpool_4")
    # deconv2_2 = deconv_layer(deconv2_1,[3,3,512,512],shape_4,"deconv2_2",training_state)
    # deconv2_3 = deconv_layer(deconv2_2,[3,3,512,512],shape_4,"deconv2_3",training_state)
    # deconv2_4 = deconv_layer(deconv2_3,[3,3,256,512],[shape_4[0],shape_4[1],shape_4[2],256],"deconv2_4",training_state)
    deconv4_2 = conv_layer(deconv4_1, "deconv4_2", [3, 3, 512, 512], training_state)
    deconv4_3 = conv_layer(deconv4_2, "deconv4_3", [3, 3, 512, 512], training_state)
    deconv4_4 = conv_layer(deconv4_3, "deconv4_4", [3, 3, 512, 256], training_state)
    # Third box of deconvolution layers(9)
    deconv3_1 = up_sampling(deconv4_4, pool3_index, shape_3, name="unpool_3")
    # deconv3_2 = deconv_layer(deconv3_1,[3,3,256,256],shape_3,"deconv3_2",training_state)
    # deconv3_3 = deconv_layer(deconv3_2,[3,3,256,256],shape_3,"deconv3_3",training_state)
    # deconv3_4 = deconv_layer(deconv3_3,[3,3,128,256],[shape_3[0],shape_3[1],shape_3[2],128],"deconv3_4",training_state)
    deconv3_2 = conv_layer(deconv3_1, "deconv3_2", [3, 3, 256, 256], training_state)
    deconv3_3 = conv_layer(deconv3_2, "deconv3_3", [3, 3, 256, 256], training_state)
    deconv3_4 = conv_layer(deconv3_3, "deconv3_4", [3, 3, 256, 128], training_state)
    # Fourth box of deconvolution layers(11)
    deconv2_1 = up_sampling(deconv3_4, pool2_index, shape_2, name="unpool_2")
    # deconv4_2 = deconv_layer(deconv4_1,[3,3,128,128],shape_2,"deconv4_2",training_state)
    # deconv4_3 = deconv_layer(deconv4_2,[3,3,64,128],[shape_2[0],shape_2[1],shape_2[2],64],"deconv4_3",training_state)
    deconv2_2 = conv_layer(deconv2_1, "deconv2_2", [3, 3, 128, 128], training_state)
    deconv2_3 = conv_layer(deconv2_2, "deconv2_3", [3, 3, 128, 64], training_state)
    # Fifth box of deconvolution layers(13)
    deconv1_1 = up_sampling(deconv2_3, pool1_index, shape_1, name="unpool1")
    # deconv5_2 = deconv_layer(deconv5_1,[3,3,64,64],shape_1,"deconv5_2",training_state)
    # deconv5_3 = deconv_layer(deconv5_2,[3,3,11,64],[shape_1[0],shape_1[1],shape_1[2],11],"deconv5_3",training_state)
    deconv1_2 = conv_layer(deconv1_1, "deconv1_2", [3, 3, 64, 64], training_state)
    deconv1_3 = conv_layer(deconv1_2, "deconv1_3", [3, 3, 64, 64], training_state)

    with tf.variable_scope('conv_classifier') as scope:
        kernel = _get_variable('weights', shape=[1, 1, 64, config["NUM_CLASSES"]], initializer=_initialization(1, 64),
                               enc=False)
        conv = tf.nn.conv2d(deconv1_3, kernel, [1, 1, 1, 1], padding='SAME')
        biases = _get_variable('biases', [config["NUM_CLASSES"]], tf.constant_initializer(0.0), enc=False)
        conv_classifier = tf.nn.bias_add(conv, biases, name=scope.name)

    loss, accuracy, prediction = cal_loss(conv_classifier, labels)
    # loss_norm, accuracy_norm, prediction_norm = Normal_Loss(conv_classifier, labels, NUM_CLASS)
    #
    # return loss_norm, accuracy_norm, prediction_norm, conv_classifier
    return loss, accuracy, prediction, conv_classifier


def max_pool(inputs, name):
    with tf.variable_scope(name) as scope:
        value, index = tf.nn.max_pool_with_argmax(tf.to_double(inputs), ksize=[1, 2, 2, 1], strides=[1, 2, 2, 1],
                                                  padding='SAME', name=scope.name)
    return tf.to_float(value), index, inputs.get_shape().as_list()


# here value is the max value, index is the corresponding index, the detail information is here
# https://www.tensorflow.org/versions/r1.0/api_docs/python/tf/nn/max_pool_with_argmax


def conv_layer(bottom, name, shape, training_state):
    """
    Inputs:
    bottom: The input image or tensor
    name: corresponding layer's name
    shape: the shape of kernel size
    training_state: represent if the weight should update 
    Output:
    The output from layers
    """
    kernel_size = shape[0]
    input_channel = shape[2]
    out_channel = shape[3]
    with tf.variable_scope(name) as scope:
        filt = _get_variable('weights', shape=shape, initializer=_initialization(kernel_size, input_channel),
                             enc=False)
        tf.summary.histogram(scope.name + "weight", filt)
        conv = tf.nn.conv2d(bottom, filt, [1, 1, 1, 1], padding='SAME')
        conv_biases = _get_variable('biases', shape=[out_channel], initializer=tf.constant_initializer(0.0),
                                    enc=False)
        tf.summary.histogram(scope.name + "bias", conv_biases)
        bias = tf.nn.bias_add(conv, conv_biases)
        conv_out = tf.nn.relu(batch_norm(bias, training_state, scope.name))

    return conv_out
    # norm is used to identify if we should use batch normalization!


def conv_layer_enc(bottom, name, shape, training_state):
    """
    Inputs:
    bottom: The input image or tensor
    name: corresponding layer's name
    shape: the shape of kernel size
    training_state: represent if the weight should update 
    Output:
    The output from layers
    """
    with tf.variable_scope(name) as scope:
        init = get_conv_filter(scope.name)
        filt = _get_variable('weights', shape=shape, initializer=init, enc=True)
        tf.summary.histogram(scope.name + "weight", filt)
        conv = tf.nn.conv2d(bottom, filt, [1, 1, 1, 1], padding='SAME')
        conv_biases_init = get_bias(scope.name)
        conv_biases = _get_variable('biases', shape=[shape[3]], initializer=conv_biases_init, enc=True)
        tf.summary.histogram(scope.name + "bias", conv_biases)
        bias = tf.nn.bias_add(conv, conv_biases)
        conv_out = tf.nn.relu(batch_norm(bias, training_state, scope.name))
    return conv_out


def batch_norm(bias_input, is_training, scope):
    return tf.cond(is_training,
                   lambda: tf.contrib.layers.batch_norm(bias_input, is_training=True, center=False, scope=scope),
                   lambda: tf.contrib.layers.batch_norm(bias_input, is_training=False, center=False, reuse=True,
                                                        scope=scope))


# is_training = Ture, it will accumulate the statistics of the movements into moving_mean and moving_variance. When it's
# not in a training mode, then it would use the values of the moving_mean, and moving_variance.
# shadow_variable = decay * shadow_variable + (1 - decay) * variable, shadow_variable, I think it's the accumulated
# moving average, and then variable is the average for this specific batch of data. For the training part,
# we need to set is_training to be True, but for the validation part, actually we should set it to be False!

def get_conv_filter(name):
    return tf.constant(vgg_param_dict[name][0], name="filter")
    # so here load the weight for VGG-16, which is kernel,
    # the kernel size for different covolution layers will show in function vgg_param_load


def get_bias(name):
    return tf.constant(vgg_param_dict[name][1], name="biases")
    # here load the bias for VGG-16, the bias size will be 64,128,256,512,512, also shown in function vgg_param_load


def up_sampling(pool, ind, output_shape, name=None):
    """
       Unpooling layer after max_pool_with_argmax.
       Args:
           pool:   max pooled output tensor
           ind:      argmax indices
           ksize:     ksize is the same as for the pool
       Return:
           unpool:    unpooling tensor
    """
    with tf.variable_scope(name):
        input_shape = pool.get_shape().as_list()
        flat_input_size = np.prod(input_shape)
        flat_output_shape = [output_shape[0], output_shape[1] * output_shape[2] * output_shape[3]]

        pool_ = tf.reshape(pool, [flat_input_size])
        batch_range = tf.reshape(tf.range(output_shape[0], dtype=ind.dtype), shape=[input_shape[0], 1, 1, 1])
        b = tf.ones_like(ind) * batch_range
        b = tf.reshape(b, [flat_input_size, 1])
        ind_ = tf.reshape(ind, [flat_input_size, 1])
        ind_ = tf.concat([b, ind_], 1)

        ret = tf.scatter_nd(ind_, pool_, shape=flat_output_shape)
        ret = tf.reshape(ret, output_shape)
    return ret


def _initialization(k, c):
    """
    Here the reference paper is https:arxiv.org/pdf/1502.01852
    k is the filter size
    c is the number of input channels in the filter tensor
    we assume for all the layers, the Kernel Matrix follows a gaussian distribution N(0, \sqrt(2/nl)), where nl is 
    the total number of units in the input, k^2c, k is the spartial filter size and c is the number of input channels. 
    Output:
    The initialized weight
    """
    std = math.sqrt(2. / (k ** 2 * c))
    return tf.truncated_normal_initializer(stddev=std)


def _get_variable(name, shape, initializer, enc):
    """
    Help to create a variable
    Inputs: 
    name: corresponding layers name, conv1 or ...
    shape: the shape of the weight or bias
    initializer: The initializer from _ínitialization
    Outputs:
    Variable tensor
    """
    if enc is True:
        var = tf.get_variable(name, initializer=initializer)
    else:
        var = tf.get_variable(name, shape, initializer=initializer)
    return var


def cal_loss(logits, labels):
    loss_weight = np.array([
        0.2595,
        0.1826,
        4.5640,
        0.1417,
        0.9051,
        0.3826,
        9.6446,
        1.8418,
        0.6823,
        6.2478,
        7.3614,
        1.0974
    ])
    # class 0 to 11, but the class 11 is ignored, so maybe the class 11 is background!

    labels = tf.to_int64(labels)
    loss, accuracy, prediction = weighted_loss(logits, labels, number_class=config["NUM_CLASSES"],
                                               frequency=loss_weight)
    return loss, accuracy, prediction


def weighted_loss(logits, labels, number_class, frequency):
    """
    The reference paper is : https://arxiv.org/pdf/1411.4734.pdf 
    Median Frequency Balancing: alpha_c = median_freq/freq(c).
    median_freq is the median of these frequencies 
    freq(c) is the number of pixles of class c divided by the total number of pixels in images where c is present
    we weight each pixels by alpha_c
    Inputs: 
    logits is the output from the inference, which is the output of the decoder layers without softmax.
    labels: true label information 
    number_class: In the CamVid data set, it's 11 classes, or 12, because class 11 seems to be background? 
    frequency: is the frequency of each class
    Outputs:
    Loss
    Accuracy
    """
    label_flatten = tf.reshape(labels, [-1])
    label_onehot = tf.one_hot(label_flatten, depth=number_class)
    logits_reshape = tf.reshape(logits, [-1, number_class])
    cross_entropy = tf.nn.weighted_cross_entropy_with_logits(targets=label_onehot, logits=logits_reshape,
                                                             pos_weight=frequency)
    cross_entropy_mean = tf.reduce_mean(cross_entropy, name='cross_entropy')
    tf.summary.scalar('loss', cross_entropy_mean)
    correct_prediction = tf.equal(tf.argmax(logits_reshape, -1), label_flatten)
    accuracy = tf.reduce_mean(tf.to_float(correct_prediction))
    # tf.summary.scalar('accuracy', accuracy)

    return cross_entropy_mean, accuracy, tf.argmax(logits_reshape, -1)


def Normal_Loss(logits, labels, number_class):
    """
    Calculate the normal loss instead of median frequency balancing
    Inputs:
    logits, the output from decoder layers, without softmax, shape [Num_batch,height,width,Number_class]
    lables: the atual label information, shape [Num_batch,height,width,1]
    number_class:12
    Output:loss,and accuracy
    Using tf.nn.sparse_softmax_cross_entropy_with_logits assume that each pixel have and only have one specific
    label, instead of having a probability belongs to labels. Also assume that logits is not softmax, because it
    will conduct a softmax internal to be efficient, this is the reason that we don't do softmax in the inference 
    function!
    """
    label_flatten = tf.to_int64(tf.reshape(labels, [-1]))
    logits_reshape = tf.reshape(logits, [-1, number_class])
    cross_entropy = tf.nn.sparse_softmax_cross_entropy_with_logits(labels=label_flatten, logits=logits_reshape,
                                                                   name='normal_cross_entropy')
    cross_entropy_mean = tf.reduce_mean(cross_entropy, name='cross_entropy')
    tf.summary.scalar('loss', cross_entropy_mean)
    correct_prediction = tf.equal(tf.argmax(logits_reshape, -1), label_flatten)
    accuracy = tf.reduce_mean(tf.cast(correct_prediction, tf.float32))
    # tf.summary.scalar('accuracy', accuracy)


    return cross_entropy_mean, accuracy, tf.argmax(logits_reshape, -1)


def train_op(total_loss):
    """
    This part is from the code 'implement slightly different for segnet in Tensorflow', basically the process are same, only
    change some part
    Input:
    total_loss: The loss 
    global_step: global_step is used to track how many batches had been passed. In the training process, the intial
    value for global_step is 0 (tf.variable(0,trainable=False)), then after one batch of images passed, the loss is
    passed into the optimizor to update the weight, then the global step increased by one. Number of batches seen 
    by the graph.. Reference: https://stackoverflow.com/questions/41166681/what-does-tensorflow-global-step-mean
    Output
    The train_op
    """
    Learning_Rate = 0.001

    # MOVING_AVERAGE_DECAY = 0.99
    # optimizer = tf.train.GradientDescentOptimizer(learning_rate = Learning_Rate)
    global_step = tf.Variable(0, trainable=False)
    update_ops = tf.get_collection(tf.GraphKeys.UPDATE_OPS)
    # variables_train = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES)

    with tf.control_dependencies(update_ops):
        optimizer = tf.train.AdamOptimizer(Learning_Rate)
        grads = optimizer.compute_gradients(total_loss, var_list=tf.trainable_variables())
        # gradients,variables = zip(*grads)
        # clipped_gradients, global_norm = (tf.clip_by_global_norm(gradients,variables))
        # clipped_grads_and_vars = zip(clipped_gradients,variables)

        training_op = optimizer.apply_gradients(grads, global_step=global_step)

    for var in tf.trainable_variables():
        tf.summary.histogram(var.op.name, var)

    for grad, var in grads:
        if grad is not None:
            tf.summary.histogram(var.op.name + '/gradients', grad)

    var = tf.get_collection(tf.GraphKeys.TRAINABLE_VARIABLES)
    grads = tf.gradients(total_loss, var)

    print("Now printing")
    print(var)
    print(grads)

    # training_op = optimizer.minimize(loss=total_loss, global_step=global_step,var_list = tf.trainable_variables())
    return training_op, global_step


def train(max_steps=101, batch_size=3):
    image_filename, label_filename = get_filename_list(config["TRAIN_FILE"], config["IMG_PREFIX"],
                                                       config["LABEL_PREFIX"])
    val_image_filename, val_label_filename = get_filename_list(config["VAL_FILE"], config["IMG_PREFIX"],
                                                               config["LABEL_PREFIX"])

    with tf.Graph().as_default():
        images_pl = tf.placeholder(tf.float32, [batch_size, config["INPUT_HEIGHT"], config["INPUT_WIDTH"],
                                                config["INPUT_CHANNELS"]])
        labels_pl = tf.placeholder(tf.int64, [batch_size, config["INPUT_HEIGHT"], config["INPUT_WIDTH"], 1])
        phase_train = tf.placeholder(tf.bool, name="phase_train")

        images_train, labels_train = dataset_inputs(image_filename, label_filename, batch_size, config["INPUT_HEIGHT"],
                                                    config["INPUT_WIDTH"], config["INPUT_CHANNELS"])
        images_val, labels_val = dataset_inputs(val_image_filename, val_label_filename, batch_size,
                                                config["INPUT_HEIGHT"], config["INPUT_WIDTH"], config["INPUT_CHANNELS"])

        loss, accuracy, prediction, logits = inference(images_train, labels_train, phase_train)
        training, global_step = train_op(total_loss=loss)
        saver = tf.train.Saver(tf.global_variables())
        summary_op = tf.summary.merge_all()
        # Merges all summaries collected in the default graph.

        with tf.Session() as sess:
            sess.run(tf.variables_initializer(tf.global_variables()))
            sess.run(tf.local_variables_initializer())

            coord = tf.train.Coordinator()
            threads = tf.train.start_queue_runners(coord=coord)

            train_loss, train_accuracy = [], []
            val_loss, val_acc = [], []
            writer = tf.summary.FileWriter(config["TB_LOGS"], graph=tf.get_default_graph())
            for step in range(max_steps):
                image_batch, label_batch = sess.run([images_train, labels_train])
                feed_dict = {images_pl: image_batch,
                             labels_pl: label_batch,
                             phase_train: True}

                _, _loss, _accuracy, summary = sess.run([training, loss, accuracy, summary_op], feed_dict=feed_dict)

                train_loss.append(_loss)
                train_accuracy.append(_accuracy)
                print("Iteration {}: Train Loss{:6.3f}, Train Accu {:6.3f}".format(step, train_loss[-1],
                                                                                   train_accuracy[-1]))

                if step % 10 == 0:
                    conv_classifier = sess.run(logits, feed_dict=feed_dict)
                    print('per_class accuracy by logits in training time',
                          per_class_acc(conv_classifier, label_batch, config["NUM_CLASSES"]))
                    print(np.argmax(conv_classifier, axis=-1))
                    # print('per class accuracy by pred in',per_class_acc(pred_2,label_batch,NUM_CLASS))
                    # per_class_acc is a function from utils
                    writer.add_summary(summary, step)

                if step % 100 == 0:
                    print("start validating.......")
                    _val_loss = []
                    _val_acc = []
                    hist = np.zeros((config["NUM_CLASSES"], config["NUM_CLASSES"]))
                    # hist2 = np.zeros((NUM_CLASS, NUM_CLASS))
                    for test_step in range(int(20)):
                        image_batch_val, label_batch_val = sess.run([images_val, labels_val])
                        feed_dict_valid = {images_pl: image_batch_val,
                                           labels_pl: label_batch_val,
                                           phase_train: True}
                        # since we still using mini-batch, so in the batch norm we set phase_train to be
                        # true, and because we didin't run the trainop process, so it will not update
                        # the weight!
                        _loss, _acc, _val_pred = sess.run([loss, accuracy, logits], feed_dict_valid)

                        _val_loss.append(_loss)
                        _val_acc.append(_acc)
                        hist += get_hist(_val_pred, label_batch_val)

                    print_hist_summary(hist)

                    val_loss.append(np.mean(_val_loss))
                    val_acc.append(np.mean(_val_acc))

                    print(
                        "Iteration {}: Train Loss {:6.3f}, Train Accu{:6.3f}, Val Loss {:6.3f}, Val Acc {:6.3f}".format(
                            step, train_loss[-1], train_accuracy[-1], val_loss[-1], val_acc[-1]))

                if step == (max_steps - 1):
                    return train_loss, train_accuracy, val_loss, val_acc
                    # checkpoint_path = os.path.join(train_dir,'model.ckpt')
                    # saver.save(sess,checkpoint_path,global_step = step)

            coord.request_stop()
            coord.join(threads)
