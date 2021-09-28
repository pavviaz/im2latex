import collections
import json
import math
from statistics import mode
import os
import random
import sys
from numpy.core.defchararray import index
import tensorflow as tf
import numpy as np
import time
import re
import shutil
import logging
import inspect
from PIL import Image
from matplotlib import pyplot as plt
from tensorflow import keras
from tensorflow.python.keras.layers.recurrent import RNN
import six
from tensorflow.python.profiler.trace import Trace
from tqdm import tqdm
from keras_preprocessing.text import tokenizer_from_json
from tensorflow.keras.layers import Dense
from tensorflow.keras.layers import Conv2D
from tensorflow.keras.layers import AveragePooling2D
from tensorflow.keras.layers import MaxPooling2D
from tensorflow.keras.layers import Dropout
from tensorflow.keras.layers import TimeDistributed
from tensorflow.keras.layers import Concatenate
from tensorflow.keras.layers import BatchNormalization
from tensorflow.keras.layers import AvgPool2D

RESIZED_IMG_H = 140
RESIZED_IMG_W = 1200
DATA_SPLIT = 1
global DATASET_PATH, ANNOTATION_FILE, tokenizer_path, tokenizer_params_path, checkpoint_path, meta_path


def InceptionV3_convolutional_model():
    image_model = tf.keras.applications.VGG16(include_top=False, weights=None)
    # image_model.trainable = False
    new_input = image_model.input
    hidden_layer = image_model.layers[-1].output
    return tf.keras.Model(new_input, hidden_layer)


def log_init(path, name):
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.INFO)

    formatter = logging.Formatter("%(asctime)s:    %(message)s")

    file_handler = logging.FileHandler(f"{path}/{name}.txt", mode="w")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler()
    stream_handler.setFormatter(formatter)

    logger.addHandler(file_handler)
    logger.addHandler(stream_handler)
    return logger


def enable_gpu(turn, gb: int = 4):  # enable of disable GPU backend
    if turn:
        os.environ['TF_FORCE_GPU_ALLOW_GROWTH'] = 'true'
        gpus = tf.config.experimental.list_physical_devices('GPU')
        if gpus:
            # Restrict TensorFlow to only allocate 1*X GB of memory on the first GPU
            try:
                tf.config.experimental.set_virtual_device_configuration(
                    gpus[0],
                    [tf.config.experimental.VirtualDeviceConfiguration(memory_limit=(1024 * gb))])
                logical_gpus = tf.config.experimental.list_logical_devices('GPU')
                print(len(gpus), "Physical GPUs,", len(logical_gpus), "Logical GPUs")
            except RuntimeError as e:
                # Virtual devices must be set before GPUs have been initialized
                print(e)
    else:
        os.environ["CUDA_VISIBLE_DEVICES"] = "-1"
        try:
            # Disable all GPUS
            tf.config.set_visible_devices([], 'GPU')
            visible_devices = tf.config.get_visible_devices()
            for device in visible_devices:
                assert device.device_type != 'GPU'
        except:
            # Invalid device or cannot modify virtual devices once initialized.
            pass


class BahdanauAttention(tf.keras.Model):
    def __init__(self, units):
        super(BahdanauAttention, self).__init__()
        self.W1 = tf.keras.layers.Dense(units)
        self.W2 = tf.keras.layers.Dense(units)
        self.V = tf.keras.layers.Dense(1)

    def call(self, features, hidden):
        # features(CNN_encoder output) shape == (batch_size, 64, embedding_dim)

        # hidden shape == (batch_size, hidden_size)
        # hidden_with_time_axis shape == (batch_size, 1, hidden_size)
        hidden_with_time_axis = tf.expand_dims(hidden, 1)

        # attention_hidden_layer shape == (batch_size, 64, units)
        attention_hidden_layer = (tf.nn.tanh(self.W1(features) +
                                             self.W2(hidden_with_time_axis)))

        # score shape == (batch_size, 64, 1)
        # This gives you an unnormalized score for each image feature.
        score = self.V(attention_hidden_layer)

        # attention_weights shape == (batch_size, 64, 1)
        attention_weights = tf.nn.softmax(score, axis=1)

        # context_vector shape after sum == (batch_size, hidden_size)
        context_vector = attention_weights * features
        context_vector = tf.reduce_sum(context_vector, axis=1)

        return context_vector, attention_weights


class CNN_Encoder(tf.keras.Model):
    m = None

    def __init__(self, embedding_dim, m=1):
        super(CNN_Encoder, self).__init__()

        self.gru = keras.layers.GRU(50,
                                       return_sequences=True,
                                       return_state=True,
                                       recurrent_initializer='glorot_uniform')
        self.rescale = tf.keras.layers.experimental.preprocessing.Rescaling(scale=1./127.5, offset=-1)
        self.flatten = tf.keras.layers.Flatten()
        self.embedding = tf.keras.layers.Embedding(1000, embedding_dim)

        self.m == m
        if m == 1:  # Epoch 41 Loss 0.332003
            self.conv1 = Conv2D(filters=16, kernel_size=(3, 3))
            self.pool1 = MaxPooling2D()
            self.conv2 = Conv2D(filters=32, kernel_size=(3, 3))
            self.pool2 = MaxPooling2D()
            self.conv3 = Conv2D(filters=64, kernel_size=(3, 3))
            self.pool3 = MaxPooling2D()
            self.conv4 = Conv2D(filters=128, kernel_size=(3, 3))
            self.pool4 = MaxPooling2D()
            self.conv5 = Conv2D(filters=256, kernel_size=(3, 3))
            self.pool5 = MaxPooling2D(pool_size=(1, 2))


        elif m == 2:  # Результат чуть хуже, чем у 1 и 3
            self.conv1 = Conv2D(filters=16, kernel_size=(3, 3))
            self.pool1 = AveragePooling2D()
            self.conv2 = Conv2D(filters=32, kernel_size=(3, 3))
            self.pool2 = AveragePooling2D()
            self.conv3 = Conv2D(filters=64, kernel_size=(3, 3))
            self.pool3 = AveragePooling2D()
            self.conv4 = Conv2D(filters=128, kernel_size=(3, 3))
            self.pool4 = AveragePooling2D()
            self.conv5 = Conv2D(filters=256, kernel_size=(3, 3))
            self.pool5 = AveragePooling2D(pool_size=(1, 2))


        elif m == 3:  # Epoch 92 Loss 0.256778
            self.conv1 = Conv2D(filters=16, kernel_size=(3, 3))
            self.pool1 = MaxPooling2D()
            self.conv2 = Conv2D(filters=32, kernel_size=(4, 4))
            self.pool2 = MaxPooling2D(pool_size=(1, 2))
            self.conv3 = Conv2D(filters=64, kernel_size=(3, 3))
            self.pool3 = MaxPooling2D()
            self.conv4 = Conv2D(filters=128, kernel_size=(4, 4))
            self.pool4 = MaxPooling2D(pool_size=(2, 1))
            self.conv5 = Conv2D(filters=256, kernel_size=(3, 3))
            self.pool5 = MaxPooling2D(pool_size=(2, 4))


        elif m == 4:  # Epoch 60 Loss 0.179976
            self.conv1 = Conv2D(filters=16, kernel_size=(3, 3))
            self.pool1 = MaxPooling2D()
            self.conv2 = Conv2D(filters=32, kernel_size=(4, 4))
            self.pool2 = MaxPooling2D(pool_size=(1, 2))
            self.conv3 = Conv2D(filters=64, kernel_size=(3, 3))
            self.pool3 = MaxPooling2D()
            self.conv4 = Conv2D(filters=128, kernel_size=(4, 4))
            self.pool4 = MaxPooling2D(pool_size=(2, 1))
            self.conv5 = Conv2D(filters=256, kernel_size=(3, 3))
            self.pool5 = MaxPooling2D(pool_size=(2, 4))
            self.conv6 = Conv2D(filters=512, kernel_size=(2, 3))


        elif m == 5:
            self.conv1_block1 = Conv2D(filters=16, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block1 = Conv2D(filters=16, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block1 = MaxPooling2D()

            self.conv1_block2 = Conv2D(filters=32, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block2 = Conv2D(filters=32, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block2 = MaxPooling2D(pool_size=(1, 2))

            self.conv1_block3 = Conv2D(filters=64, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block3 = Conv2D(filters=64, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block3 = MaxPooling2D()

            self.conv1_block4 = Conv2D(filters=128, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block4 = Conv2D(filters=128, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block4 = MaxPooling2D(pool_size=(2, 1))

            self.conv1_block5 = Conv2D(filters=256, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block5 = Conv2D(filters=256, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block5 = MaxPooling2D(pool_size=(3, 5))

            self.conv1_block6 = Conv2D(filters=512, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block6 = Conv2D(filters=512, kernel_size=(3, 3), padding='same', activation='relu')


        elif m == 6:
            self.conv1 = Conv2D(filters=16, kernel_size=(3, 3))
            self.pool1 = MaxPooling2D()
            self.conv2 = Conv2D(filters=32, kernel_size=(4, 4))
            self.pool2 = MaxPooling2D(pool_size=(1, 2))
            self.conv3 = Conv2D(filters=64, kernel_size=(3, 3))
            self.pool3 = MaxPooling2D()
            self.conv4 = Conv2D(filters=128, kernel_size=(4, 4))
            self.pool4 = MaxPooling2D(pool_size=(2, 1))
            self.conv5 = Conv2D(filters=256, kernel_size=(3, 3))
            self.pool5 = MaxPooling2D(pool_size=(2, 4))
            self.conv6 = Conv2D(filters=512, kernel_size=(2, 3))


        elif m == 7:
            self.conv1_block1 = Conv2D(filters=16, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block1 = Conv2D(filters=16, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block1 = MaxPooling2D(pool_size=(2, 3))

            self.conv1_block2 = Conv2D(filters=32, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block2 = Conv2D(filters=32, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block2 = MaxPooling2D(pool_size=(2, 3))

            self.conv1_block3 = Conv2D(filters=64, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block3 = Conv2D(filters=64, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block3 = MaxPooling2D()

            self.conv1_block4 = Conv2D(filters=128, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block4 = Conv2D(filters=128, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block4 = MaxPooling2D(pool_size=(1, 2))

            self.conv1_block5 = Conv2D(filters=256, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block5 = Conv2D(filters=256, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block5 = MaxPooling2D(pool_size=(2, 3))

            self.conv1_block6 = Conv2D(filters=512, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block6 = Conv2D(filters=512, kernel_size=(3, 3), padding='same', activation='relu')


        elif m == 8:
            self.conv1_block1 = Conv2D(filters=64, kernel_size=(3, 3), padding='same', activation='relu')
            # self.conv2_block1 = Conv2D(filters=64, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block1 = MaxPooling2D(pool_size=(2, 3))

            self.conv1_block2 = Conv2D(filters=128, kernel_size=(3, 3), padding='same', activation='relu')
            # self.conv2_block2 = Conv2D(filters=128, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block2 = MaxPooling2D(pool_size=(2, 3))

            self.conv1_block3 = Conv2D(filters=256, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block3 = Conv2D(filters=256, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block3 = MaxPooling2D(pool_size=(1, 2))

            self.conv1_block4 = Conv2D(filters=512, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block4 = MaxPooling2D(pool_size=(2, 3))
            self.conv2_block4 = Conv2D(filters=512, kernel_size=(3, 3), padding='same', activation='relu')

            # self.conv1_block5 = Conv2D(filters=256, kernel_size=(3, 3), padding='same', activation='relu')
            # self.conv2_block5 = Conv2D(filters=256, kernel_size=(3, 3), padding='same', activation='relu')
            # self.pool_block5 = MaxPooling2D(pool_size=(2, 3))

            # self.conv1_block6 = Conv2D(filters=512, kernel_size=(3, 3), padding='same', activation='relu')
            # self.conv2_block6 = Conv2D(filters=512, kernel_size=(3, 3), padding='same', activation='relu')
        

        elif m == 9:
            self.conv1_block1 = Conv2D(filters=64, kernel_size=(5, 5), padding='valid', activation='relu')
            # self.conv2_block1 = Conv2D(filters=64, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block1 = MaxPooling2D(pool_size=(2, 3))

            self.conv1_block2 = Conv2D(filters=128, kernel_size=(5, 5), padding='valid', activation='relu')
            # self.conv2_block2 = Conv2D(filters=128, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block2 = MaxPooling2D(pool_size=(2, 3))

            self.conv1_block3 = Conv2D(filters=256, kernel_size=(5, 5), padding='valid', activation='relu')
            self.conv2_block3 = Conv2D(filters=256, kernel_size=(5, 5), padding='same', activation='relu')
            self.pool_block3 = MaxPooling2D(pool_size=(2, 4))

            self.conv1_block4 = Conv2D(filters=512, kernel_size=(5, 5), padding='same', activation='relu')
            self.pool_block4 = MaxPooling2D(pool_size=(1, 2))
            self.conv2_block4 = Conv2D(filters=512, kernel_size=(5, 5), padding='same', activation='relu')


        elif m == 10:
            self.conv1_block1 = Conv2D(filters=64, kernel_size=(3, 3), padding='same', activation='relu')
            # self.conv2_block1 = Conv2D(filters=64, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block1 = MaxPooling2D(pool_size=(2, 2))

            self.conv1_block2 = Conv2D(filters=128, kernel_size=(3, 3), padding='same', activation='relu')
            # self.conv2_block2 = Conv2D(filters=128, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block2 = MaxPooling2D(pool_size=(4, 4))

            self.conv1_block3 = Conv2D(filters=256, kernel_size=(3, 3), padding='same', activation='relu')
            self.conv2_block3 = Conv2D(filters=256, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block3 = MaxPooling2D(pool_size=(2, 2))

            self.conv1_block4 = Conv2D(filters=512, kernel_size=(3, 3), padding='same', activation='relu')
            self.pool_block4 = MaxPooling2D(pool_size=(2, 2))
            self.conv2_block4 = Conv2D(filters=512, kernel_size=(3, 3), padding='same', activation='relu')
        
        
        elif m == 11:
            self.initial = Conv2D(64, (7,7), strides=2, activation='relu')
            self.max_pooling_initial = MaxPooling2D(pool_size=(2,2))

            self.batch_1_batchNorm = BatchNormalization()
            self.batch_1_conv2d_1 = Conv2D(128, (1,1), activation='relu', padding='same')
            self.batch_1_drop = Dropout(0.3)
            self.batch_1_conv2d_2 = Conv2D(32, (3,3), activation='relu', padding='same')

            self.batch_2 = Concatenate()

            self.batch_2_batchNorm = BatchNormalization()
            self.batch_2_conv2d_1 = Conv2D(128, (1,1), activation='relu', padding='same')
            self.batch_2_drop = Dropout(0.4)
            self.batch_2_conv2d_2 = Conv2D(32, (3,3), activation='relu', padding='same')

            self.batch_3 = Concatenate()

            self.batch_3_batchNorm = BatchNormalization()
            self.batch_3_conv2d_1 = Conv2D(128, (1,1), activation='relu', padding='same')
            self.batch_3_drop = Dropout(0.4)
            self.batch_3_conv2d_2 = Conv2D(32, (3,3), activation='relu', padding='same')

            self.batch_4 = Concatenate()

            self.batch_4_batchNorm = BatchNormalization()
            self.batch_4_conv2d_1 = Conv2D(128, (1,1), activation='relu', padding='same')
            self.batch_4_drop = Dropout(0.4)
            self.batch_4_conv2d_2 = Conv2D(32, (3,3), activation='relu', padding='same')

            self.final_batch = Concatenate()

            self.downsampling_batchNorm = BatchNormalization()
            self.downsampling_conv2d_1 = Conv2D(32, (1,1), activation='relu')
            self.downsampling_avg = AvgPool2D(pool_size=(4,4), strides=4)
        

        elif m == 12:
            self.model = InceptionV3_convolutional_model()

        self.fc_00 = Dense(embedding_dim)
        self.fc_0 = Dense(embedding_dim)
        self.do_0 = Dropout(0.15)
        self.do_1 = Dropout(0.5)
        # shape after fc == (batch_size, 64, embedding_dim)
        self.fc = Dense(embedding_dim)

    def call(self, x):
        # print(f"init shape = {x.shape}")

        x = self.rescale(x)
        # print(f"rescale shape = {x.shape}")

        x = self.conv1_block1(x)
        # x = self.conv2_block1(x)
        x = self.pool_block1(x)

        x = self.conv1_block2(x)
        # x = self.conv2_block2(x)
        x = self.pool_block2(x)

        x = self.conv1_block3(x)
        x = self.conv2_block3(x)
        x = self.pool_block3(x)

        x = self.conv1_block4(x)
        x = self.pool_block4(x)
        x = self.conv2_block4(x)

        # x = self.conv1_block5(x)
        # x = self.conv2_block5(x)
        # x = self.pool_block5(x)

        # x = self.conv1_block6(x)
        # x = self.conv2_block6(x)
        # x = self.pool_block6(x)


        # x = self.initial(x)
        # x = self.max_pooling_initial(x)
        # t_x = x

        # x = self.batch_1_batchNorm(x)
        # x = tf.nn.relu(x)
        # x = self.batch_1_conv2d_1(x)
        # x = self.batch_1_drop(x)
        # x = self.batch_1_conv2d_2(x)

        # x = self.batch_2([t_x, x])
        # t_x = x

        # x = self.batch_2_batchNorm(x)
        # x = tf.nn.relu(x)
        # x = self.batch_2_conv2d_1(x)
        # x = self.batch_2_drop(x)
        # x = self.batch_2_conv2d_2(x)

        # x = self.batch_3([t_x, x])
        # t_x = x

        # x = self.batch_3_batchNorm(x)
        # x = tf.nn.relu(x)
        # x = self.batch_3_conv2d_1(x)
        # x = self.batch_3_drop(x)
        # x = self.batch_3_conv2d_2(x)

        # x = self.batch_4([t_x, x])
        # t_x = x

        # x = self.batch_4_batchNorm(x)
        # x = tf.nn.relu(x)
        # x = self.batch_4_conv2d_1(x)
        # x = self.batch_4_drop(x)
        # x = self.batch_4_conv2d_2(x)

        # x = self.final_batch([x, t_x])

        # x = self.downsampling_batchNorm(x)
        # x = tf.nn.relu(x)
        # x = self.downsampling_conv2d_1(x)
        # x = self.downsampling_avg(x)
        

        # fmaps = []
        # for fmap in x:
        #     fmaps.append(self.gru(fmap))
            
        # x = self.outer_comp(x)

        x = tf.reshape(x, (x.shape[0], -1, x.shape[3]))
        print(f"reshape_shape = {x.shape}")

        # x = self.add_timing_signal_nd(x)

        # x, _ = self.gru(x)
        # print(f"gru = {x}")
        # print(f"gru = {h.shape}")
        
        # x = self.fc_00(x)
        # x = tf.nn.relu(x)

        # x = self.do_0(x)

        # x = self.fc_0(x)
        # x = tf.nn.relu(x)

        #x = self.do_1(x)

        x = self.fc(x)
        x = tf.nn.relu(x)
        print(f"final = {x.shape}")
        return x

    def outer_comp(self, x):
        return tf.stack(x)


    def add_timing_signal_nd(self, x, min_timescale=5.0, max_timescale=1.0e4):
        """Adds a bunch of sinusoids of different frequencies to a Tensor.
        Each channel of the input Tensor is incremented by a sinusoid of a different
        frequency and phase in one of the positional dimensions.
        This allows attention to learn to use absolute and relative positions.
        Timing signals should be added to some precursors of both the query and the
        memory inputs to attention.
        The use of relative position is possible because sin(a+b) and cos(a+b) can be
        experessed in terms of b, sin(a) and cos(a).
        x is a Tensor with n "positional" dimensions, e.g. one dimension for a
        sequence or two dimensions for an image
        We use a geometric sequence of timescales starting with
        min_timescale and ending with max_timescale.  The number of different
        timescales is equal to channels // (n * 2). For each timescale, we
        generate the two sinusoidal signals sin(timestep/timescale) and
        cos(timestep/timescale).  All of these sinusoids are concatenated in
        the channels dimension.
        Args:
            x: a Tensor with shape [batch, d1 ... dn, channels]
            min_timescale: a float
            max_timescale: a float
        Returns:
            a Tensor the same shape as x.
        """
        static_shape = x.get_shape().as_list()
        num_dims = len(static_shape) - 2
        channels = tf.shape(x)[-1]
        num_timescales = channels // (num_dims * 2)
        log_timescale_increment = (
            math.log(float(max_timescale) / float(min_timescale)) /
            (tf.compat.v1.to_float(num_timescales) - 1))
        inv_timescales = min_timescale * tf.exp(
            tf.compat.v1.to_float(tf.range(num_timescales)) * -log_timescale_increment)
        for dim in six.moves.xrange(num_dims):
            length = tf.shape(x)[dim + 1]
            position = tf.compat.v1.to_float(tf.range(length))
            scaled_time = tf.expand_dims(position, 1) * tf.expand_dims(
                inv_timescales, 0)
            signal = tf.concat([tf.sin(scaled_time), tf.cos(scaled_time)], axis=1)
            prepad = dim * 2 * num_timescales
            postpad = channels - (dim + 1) * 2 * num_timescales
            signal = tf.pad(signal, [[0, 0], [prepad, postpad]])
            for _ in six.moves.xrange(1 + dim):
                signal = tf.expand_dims(signal, 0)
            for _ in six.moves.xrange(num_dims - 1 - dim):
                signal = tf.expand_dims(signal, -2)
            x += signal
        return x


class RNN_Decoder(tf.keras.Model):
    def __init__(self, embedding_dim, units, vocab_size):
        super(RNN_Decoder, self).__init__()
        self.units = units

        self.embedding = tf.keras.layers.Embedding(vocab_size, embedding_dim)
        self.gru = tf.keras.layers.GRU(self.units,
                                       return_sequences=True,
                                       return_state=True,
                                       recurrent_initializer='glorot_uniform')

        self.llstm = tf.keras.layers.LSTM(self.units,
                                       return_sequences=True,
                                       return_state=True,
                                       recurrent_initializer='glorot_uniform')

        self.gru_cuda = tf.compat.v1.keras.layers.CuDNNGRU(units, 
                                        return_sequences=True, 
                                        return_state=True, 
                                        recurrent_initializer='glorot_uniform')

        self.lstm = tf.keras.layers.LSTMCell(self.units,
                                             recurrent_initializer='glorot_uniform')

        self.fc1 = tf.keras.layers.Dense(self.units)
        self.fc2 = tf.keras.layers.Dense(vocab_size)

        self.attention = BahdanauAttention(self.units)

        self.dropout = tf.keras.layers.Dropout(0.5)
        self.b_n = tf.keras.layers.BatchNormalization()

        self.get_initial_state = self.lstm.get_initial_state
        

    def call(self, x, features, state_output, hidden):
        # defining attention as a separate mod`el
        context_vector, attention_weights = self.attention(features, state_output)

        # x shape after passing through embedding == (batch_size, 1, embedding_dim)
        x = self.embedding(x)

        # x shape after concatenation == (batch_size, 1, embedding_dim + hidden_size)
        x = tf.concat([context_vector, tf.squeeze(x, axis=1)], axis=-1)

        # passing the concatenated vector to the GRU
        state_output, state = self.lstm(x, hidden)

        # shape == (batch_size, max_length, hidden_size)
        x = self.fc1(state_output)

        # x shape == (batch_size * max_length, hidden_size)
        # x = tf.reshape(x, (-1, x.shape[2]))

        # x = self.dropout(x)
        # x = self.b_n(x)

        # output shape == (batch_size * max_length, vocab)
        x = self.fc2(x)

        return x, state_output, state, attention_weights

    def reset_state(self, batch_size):
        return tf.zeros((batch_size, self.units))


class Rnn_Global_Decoder(tf.keras.Model):
    def __init__(self, embedding_dim, units, vocab_size,scoring_type = "dot"):
        super(Rnn_Global_Decoder, self).__init__()

        self.units = units
        self.embedding = tf.keras.layers.Embedding(vocab_size, embedding_dim)

        self.gru = tf.keras.layers.GRU(self.units,
                                   return_sequences=True,
                                   return_state=True,
                                   recurrent_initializer='glorot_uniform')
        
        self.wc = tf.keras.layers.Dense(units, activation='tanh')
        self.ws = tf.keras.layers.Dense(vocab_size)

        #For Attention
        self.wa = tf.keras.layers.Dense(units)
        self.wb = tf.keras.layers.Dense(units)
        
        #For Score 3 i.e. Concat score
        self.Vattn = tf.keras.layers.Dense(1)
        self.wd = tf.keras.layers.Dense(units, activation='tanh')

        self.scoring_type = scoring_type

        
    def call(self, sequence, features, hidden):
        
        # features : (64,49,256)
        # hidden : (64,512)
        
        embed = self.embedding(sequence)
        # embed ==> (64,1,256) ==> decoder_input after embedding (embedding dim=256)
       
        output, state = self.gru(embed)       
        #output :(64,1,512)

        score=0
        
        #Dot Score as per paper(Dot score : h_t (dot) h_s') (NB:just need to tweak gru units to 256)
        '''----------------------------------------------------------'''
        if(self.scoring_type=='dot'):
          xt=output #(64,1,512)
          xs=features #(256,49,64)  
          score = tf.matmul(xt, xs, transpose_b=True) 
               
          #score : (64,1,49)

        '''----------------------------------------------------------'''
        '''----------------------------------------------------------'''



        # General Score as per Paper ( General score: h_t (dot) Wa (dot) h_s')
        '''----------------------------------------------------------'''
        if(self.scoring_type=='general'):
          score = tf.matmul(output, self.wa(features), transpose_b=True)
          # score :(64,1,49)
        '''----------------------------------------------------------'''
        '''----------------------------------------------------------'''




        # Concat score as per paper (score: VT*tanh(W[ht;hs']))    
        '''----------------------------------------------------------'''
        #https://www.tensorflow.org/api_docs/python/tf/tile
        if(self.scoring_type=='concat'):
          tiled_features = tf.tile(features, [1,1,2]) #(64,49,512)
          tiled_output = tf.tile(output, [1,148,1]) #(64,49,512)
          
          concating_ht_hs = tf.concat([tiled_features,tiled_output],2) ##(64,49,1024)
          
          tanh_activated = self.wd(concating_ht_hs)
          score =self.Vattn(tanh_activated)
          #score :(64,49,1), but we want (64,1,49)
          score= tf.squeeze(score, 2)
          #score :(64,49)
          score = tf.expand_dims(score, 1)
          
          #score :(64,1,49)
        '''----------------------------------------------------------'''
        '''----------------------------------------------------------'''



        # alignment vector a_t
        alignment = tf.nn.softmax(score, axis=2)
        # alignment :(64,1,49)

        # context vector c_t is the average sum of encoder output
        context = tf.matmul(alignment, features)
        # context : (64,1,256)
        
        # Combine the context vector and the LSTM output
        
        output = tf.concat([tf.squeeze(context, 1), tf.squeeze(output, 1)], 1)
        # output: concat[(64,1,256):(64,1,512)] = (64,768)

        output = self.wc(output)
        # output :(64,512)

        # Finally, it is converted back to vocabulary space: (batch_size, vocab_size)
        logits = self.ws(output)
        # logits/predictions: (64,8239) i.e. (batch_size,vocab_size))

        return logits, state, alignment

    def reset_state(self, batch_size):
        return tf.zeros((batch_size, self.units))



class Training:
    global DATASET_PATH, ANNOTATION_FILE

    manager = None

    def __init__(self, manager, **params):
        global meta_path
        self.tokenizer = None
        self.img_to_cap_vector = None

        self.manager = manager
        self.top_k = params["top_k"]
        self.image_count = params["image_count"]
        self.BATCH_SIZE = params["BATCH_SIZE"]
        self.BUFFER_SIZE = params["BUFFER_SIZE"]
        self.embedding_dim = params["embedding_dim"]
        self.units = params["units"]
        self.vocab_size = self.top_k + 1
        self.EPOCHS = params["EPOCHS"]
        self.conv_var = params["conv_var"]

        print("Deleting temporary files, please wait...")
        self.manager.remove_temp()

        os.makedirs(os.path.dirname(meta_path), exist_ok=True)
        with open(meta_path, "w") as meta:
            for param in params.values():
                meta.write(str(param) + ";")

        self.logger = log_init(manager.get_model_path(), "model_log")
        self.logger.info(f"Model '{manager.get_model_path()}' has been created with these params:")
        for k, v in params.items():
            self.logger.info(f"{k} - {v}")

        self.logger.info(f"---------------MODEL AND UTILS SUMMARY---------------")
        self.logger.info(f"ENCODER_INIT:\n{inspect.getsource(CNN_Encoder.__init__)}")
        self.logger.info(f"ENCODER_CALL:\n{inspect.getsource(CNN_Encoder.call)}")
        self.logger.info(f"IMG_PREPROCESSING:\n{inspect.getsource(self.load_image)}")
        self.logger.info(f"RESIZE_HEIGHT: {RESIZED_IMG_H}")
        self.logger.info(f"RESIZE_WIDTH: {RESIZED_IMG_W}")
        self.logger.info(f"DATA_SPLIT_INDEX: {DATA_SPLIT}")
        self.logger.info(f"-----------------------------------------------------")


    def auto_train(self):
        self.data_preprocess()
        self.train()


    def loss_function(self, real, pred, loss_object):
        # print(f"real = {real}  ;  pred = {pred}")
        # tf.print(real)
        # tf.print(pred)

        mask = tf.math.logical_not(tf.math.equal(real, 0))

        # tf.print(mask)

        loss_ = loss_object(real, pred)

        # tf.print(loss_)

        mask = tf.cast(mask, dtype=loss_.dtype)
        loss_ *= mask
        # tf.print(loss_)
        # tf.print(tf.reduce_mean(loss_))
        # print(f"loss = {loss_}")
        return tf.reduce_mean(loss_)


    @staticmethod
    def plot_attention(image, result, attention_plot):
        # temp_image = np.array(Image.open(image).convert('RGB'))

        # fig = plt.figure(figsize=(10, 10))

        # len_result = len(result)
        # for i in range(len_result):
        #     temp_att = np.resize(attention_plot[i], (4, 37))
        #     grid_size = max(np.ceil(len_result / 2), 2)
        #     ax = fig.add_subplot(grid_size, grid_size, i + 1)
        #     ax.set_title(result[i])
        #     img = ax.imshow(temp_image)
        #     ax.imshow(temp_att, cmap='gray', alpha=0.6, extent=img.get_extent())

        # #plt.tight_layout()
        # plt.show()

        plotting = []
        for _ in range(len(result)):
            plotting.append(plt.imread(image))  # real ; pred ; plt image

        fig, axes = plt.subplots(nrows=2, ncols=1)

        for ax, plot, i in zip(axes.flat, plotting, range(len(result))):
            temp_att = np.resize(attention_plot[i], (4, 37))
            img = ax.imshow(plot)
            ax.set_title(result[i])
            ax.axis('off')
            ax.imshow(temp_att, cmap='gray', alpha=0.6, extent=img.get_extent())
        plt.show()


    @tf.function
    def train_step(self, img_tensor, target, decoder, encoder, optimizer, loss_object):
        loss = 0

        # initializing the hidden state for each batch
        # because the captions are not related from image to image
        #hidden = decoder.reset_state(batch_size=target.shape[0])
        hidden = decoder.get_initial_state(batch_size=target.shape[0], dtype="float32")
        state_out = hidden[0] 

        dec_input = tf.expand_dims([self.tokenizer.word_index['<start>']] * target.shape[0], 1)

        with tf.GradientTape() as tape:
            features = encoder(img_tensor)
            # hidden = hidden_enc

            for i in range(1, target.shape[1]):
                # passing the features through the decoder
                predictions, state_out, hidden, _ = decoder(dec_input, features, state_out, hidden)

                loss += self.loss_function(target[:, i], predictions, loss_object)

                # using teacher forcing
                dec_input = tf.expand_dims(target[:, i], 1)

        total_loss = (loss / int(target.shape[1]))

        trainable_variables = encoder.trainable_variables + decoder.trainable_variables

        gradients = tape.gradient(loss, trainable_variables)

        optimizer.apply_gradients(zip(gradients, trainable_variables))

        return loss, total_loss


    # def save_convoluted_images(self, dataset):
    #     for img, path in tqdm(dataset):
    #         batch_features = image_features_extract_model(img)
    #         print(tf.shape(batch_features).numpy())
    #         batch_features = tf.reshape(batch_features,
    #                                     (batch_features.shape[0], -1, batch_features.shape[3]))
    #         print(tf.shape(batch_features).numpy())
    #         for bf, p in zip(batch_features, path):
    #             path_of_feature = p.numpy().decode("utf-8")
    #             np.save(path_of_feature, bf.numpy())  # сохранить извлеченные признаки в форме (16, ?, 2048)


    def save_reshaped_images(self, dataset):
        for img, path in tqdm(dataset):
            for im, p in zip(img, path):
                path_of_feature = p.numpy().decode("utf-8")
                np.save(path_of_feature, im.numpy())  # сохранить извлеченные признаки в форме (16, ?, 2048)


    # Find the maximum length of any caption in our dataset
    def calc_max_length(self, tensor):
        return max(len(t) for t in tensor)


    # Load the numpy files
    def map_func(self, img_name, cap):
        img = tf.io.read_file(img_name.decode("utf-8"))
        img = tf.image.decode_png(img, channels=3)
        img = tf.image.resize(img, (RESIZED_IMG_H, RESIZED_IMG_W), method=tf.image.ResizeMethod.GAUSSIAN,
                              antialias=True)
        # print(tf.image.convert_image_dtype(img, dtype=tf.float32))
        # img = tf.image.convert_image_dtype(img, dtype=tf.float32)
        # img_tensor = np.load(img_name.decode('utf-8') + '.npy')
        return img.numpy(), cap


    @staticmethod
    def load_image(image_path):
        img = tf.io.read_file(image_path)
        img = tf.image.decode_png(img, channels=3)
        # img = tf.image.convert_image_dtype(img, dtype=tf.float32)
        img = tf.image.resize(img, (RESIZED_IMG_H, RESIZED_IMG_W), method=tf.image.ResizeMethod.GAUSSIAN,
                              antialias=True)
        # img = tf.image.rgb_to_grayscale(img)
        # Image.fromarray(np.asarray(img.numpy().astype(np.uint8))).show()
        return img, image_path


    def get_image_to_caption(self, annotations_file):
        image_path_to_caption = collections.defaultdict(list)  # словарь, в который автоматически будет добавляться лист
        # при попытке доступа к несущестувующему ключу
        for val in annotations_file['annotations']:
            caption = f"<start> {val['caption']} <end>"
            image_path = DATASET_PATH + val["image_id"] + ".png"
            image_path_to_caption[image_path].append(
                caption)  # словарь типа 'путь_фото': ['описание1', 'описание2', ...]

        return image_path_to_caption


    def data_preprocess(self):  # составление токенайзера
        global tokenizer_path, tokenizer_params_path

        with open(ANNOTATION_FILE, 'r') as f:
            annotations = json.load(f)

        image_path_to_caption = self.get_image_to_caption(annotations)

        image_paths = list(image_path_to_caption.keys())
        random.shuffle(image_paths)

        # for k, v in image_path_to_caption.items():
        #     print(f"key = {k} ; value = {v}")

        train_image_paths = image_paths[:self.image_count]  # берется только 6000 верхних фото
        self.logger.info(
            f"Annotations and image paths have been successfully extracted from {ANNOTATION_FILE}\ntotal images count - {len(train_image_paths)}")

        train_captions = []  # описания для тренировки
        img_name_vector = []  # пути к фото

        for image_path in train_image_paths:
            caption_list = image_path_to_caption[image_path]
            train_captions.extend(caption_list)
            img_name_vector.extend([image_path] * len(caption_list))

        # print(img_name_vector[:5])  # 5 одинаковых путей к фото соответсвуют 5 разных описаний
        # print(train_captions[:5])

        # Получение уникальных путей к фото
        encode_train = sorted(set(img_name_vector))

        # Feel free to change batch_size according to your system configuration
        image_dataset = tf.data.Dataset.from_tensor_slices(encode_train)
        image_dataset = image_dataset.map(
            Training.load_image, num_parallel_calls=tf.data.AUTOTUNE).batch(64)

        # print(list(image_dataset)[:100])  # после мэппинга и препроцессинга получаются тензоры формы (16, 299, 299, 3)
        self.logger.info(f"Images are being preprocessed and saved...")
        start = time.time()
        try:
            pass
            # self.save_reshaped_images(image_dataset)
        except:
            self.logger.error("Something went wrong!")
            self.manager.remove_temp()
            sys.exit()

        self.logger.info(f"Done in {time.time() - start:.2f} sec")

        os.makedirs(os.path.dirname(tokenizer_path), exist_ok=True)
        with open(tokenizer_path, 'w', encoding='utf-8') as f:
            # Choose the top top_k words from the vocabulary
            self.tokenizer = tf.keras.preprocessing.text.Tokenizer(num_words=self.top_k, split=' ', oov_token="<unk>",
                                                                   lower=False, filters='%')

            self.tokenizer.fit_on_texts(train_captions)
            self.tokenizer.word_index['<pad>'] = 0
            self.tokenizer.index_word[0] = '<pad>'  # создание токенайзера и сохранение его в json

            tokenizer_json = self.tokenizer.to_json()
            f.write(json.dumps(tokenizer_json, ensure_ascii=False))

        self.logger.info("\nTokenizer has been created with params:")
        for k, v in self.tokenizer.get_config().items():
            self.logger.info(f"{k} - {v}")

        # Create the tokenized vectors
        train_seqs = self.tokenizer.texts_to_sequences(
            train_captions)  # преобразование текста в последовательность чисел
        # print(train_seqs[:100])

        # Pad each vector to the max_length of the captions
        # If you do not provide a max_length value, pad_sequences calculates it automatically
        cap_vector = tf.keras.preprocessing.sequence.pad_sequences(train_seqs, padding='post')  # приведение всех
        # последовательностей к одинаковой длине
        # print(cap_vector[:100])

        # Calculates the max_length, which is used to store the attention weights

        os.makedirs(os.path.dirname(tokenizer_params_path), exist_ok=True)
        with open(tokenizer_params_path, 'w') as f:
            max_length = self.calc_max_length(train_seqs)
            f.write(str(max_length))

        self.img_to_cap_vector = collections.defaultdict(list)
        for img, cap in zip(img_name_vector, cap_vector):
            self.img_to_cap_vector[img].append(cap)

        self.logger.info(f"Img_to_cap vector is compiled. Max cap length - {max_length}")
        # for k, v in self.img_to_cap_vector.items():
        #     print(f"key = {k} ; value = {v}")


    def train(self):
        global checkpoint_path
        # Create training and validation sets using an 80-20 split randomly.
        img_keys = list(self.img_to_cap_vector.keys())
        random.shuffle(img_keys)
        # print(img_keys[:100])

        slice_index = int(len(img_keys) * DATA_SPLIT)
        img_name_train_keys, img_name_val_keys = img_keys[:slice_index], img_keys[slice_index:]

        img_name_train = []
        cap_train = []
        for imgt in img_name_train_keys:  # тут теперь идут все фотки, а не только 80%
            capt_len = len(self.img_to_cap_vector[imgt])
            img_name_train.extend([imgt] * capt_len)
            cap_train.extend(self.img_to_cap_vector[imgt])

        img_name_val = []
        cap_val = []
        for imgv in img_name_val_keys:
            capv_len = len(self.img_to_cap_vector[imgv])
            img_name_val.extend([imgv] * capv_len)
            cap_val.extend(self.img_to_cap_vector[imgv])

        # print(img_name_train[:20])
        # print(cap_train[:20])
        self.logger.info(
            f"Dataset has been splitted:\nIMG_TRAIN - {len(img_name_train)}\nCAP_TRAIN - {len(cap_train)}\nIMG_VAL - {len(img_name_val)}\nCAP_VAL - {len(cap_val)}")

        num_steps = len(img_name_train) // self.BATCH_SIZE
        dataset = tf.data.Dataset.from_tensor_slices((img_name_train, cap_train))
        # Use map to load the numpy files in parallel
        dataset = dataset.map(lambda item1, item2: tf.numpy_function(
            self.map_func, [item1, item2], [tf.float32, tf.int32]),
                              num_parallel_calls=tf.data.AUTOTUNE)

        # Shuffle and batch
        dataset = dataset.shuffle(self.BUFFER_SIZE).batch(self.BATCH_SIZE)
        dataset = dataset.prefetch(buffer_size=tf.data.AUTOTUNE)
        self.logger.info(f"Dataset is ready")

        # инициализация параметров нейросети
        encoder = CNN_Encoder(self.embedding_dim, m=self.conv_var)
        decoder = RNN_Decoder(self.embedding_dim, self.units, self.vocab_size)

        optimizer = tf.keras.optimizers.RMSprop()
        loss_object = tf.keras.losses.SparseCategoricalCrossentropy(
            from_logits=True, reduction='none')

        ckpt = tf.train.Checkpoint(encoder=encoder,
                                   decoder=decoder,
                                   optimizer=optimizer)
        ckpt_manager = tf.train.CheckpointManager(ckpt, checkpoint_path, max_to_keep=10)

        self.logger.info(f"OPTIMIZER SUMMARY:\n{optimizer.get_config()}")
        # start_epoch = 0
        # if ckpt_manager.latest_checkpoint:
        #     start_epoch = int(ckpt_manager.latest_checkpoint.split('-')[-1])
        #     # restoring the latest checkpoint in checkpoint_path
        #     ckpt.restore(ckpt_manager.latest_checkpoint)

        # adding this in a separate cell because if you run the training cell
        # many times, the loss_plot array will be reset
        loss_plot = []

        for epoch in range(self.EPOCHS):
            start = time.time()
            total_loss = 0

            for (batch, (img_tensor, target)) in tqdm(enumerate(dataset)):
                # print(f"img_tensor shape = {img_tensor.shape}")
                # print(f"target shape = {target.shape}")

                # print(img_tensor.numpy())
                # print(target.numpy())
                batch_loss, t_loss = self.train_step(img_tensor, target, decoder, encoder, optimizer, loss_object)
                total_loss += t_loss

                if batch % 100 == 0:
                    average_batch_loss = batch_loss.numpy() / int(target.shape[1])
                    self.logger.info(
                        f'Epoch {epoch + 1} Batch {batch} Loss = {batch_loss.numpy()} / {int(target.shape[1])} = {average_batch_loss:.4f}')
            # storing the epoch end loss value to plot later
            loss_plot.append(total_loss / num_steps)

            ckpt_manager.save()
            self.logger.info(f"Epoch {epoch} checkpoint saved!")

            self.logger.info(f'Epoch {epoch + 1} Loss {total_loss / num_steps:.6f}')
            self.logger.info(f'Time taken for 1 epoch {time.time() - start:.2f} sec\n')

        self.logger.info(f"Training is done!")

        plt.plot(loss_plot)
        plt.xlabel('Epochs')
        plt.ylabel('Loss')
        plt.title('Loss Plot')
        plt.show()

        print("Deleting temporary files, please wait...")
        self.manager.remove_temp()


class Prediction:
    def __init__(self):
        global meta_path
        self.max_length = None
        self.tokenizer = None
        try:
            with open(meta_path, "r") as meta:
                reg = re.findall(r"\w+", meta.readline())
                self.vocab_size = int(reg[0]) + 1
                self.units = int(reg[5])
                self.embedding_dim = int(reg[4])
        except:
            raise IOError("Meta file reading failed")


    def index(self, array, item):
        for idx, val in np.ndenumerate(array):
            if val == item:
                return idx[1]
            

    def find_n_best(self, array, n):
        probs = [np.partition(array[0], i)[i] for i in range(-1, -n - 1, -1)]
        ids = [self.index(array, p) for p in probs]
        return [[prob, id] for prob, id in zip(probs, ids)]


    def beam_evaluate(self, image, decoder, encoder, beam_width=10):
        global checkpoint_path
        attention_plots = [np.zeros((self.max_length, 148)) for _ in range(beam_width)] 

        hidden = decoder.get_initial_state(batch_size=1, dtype="float32")
        state_out = hidden[0] 

        temp_input = tf.expand_dims(Training.load_image(image)[0], 0)

        features = encoder(temp_input)
        # hidden = hidden_enc

        dec_input = tf.expand_dims([self.tokenizer.word_index['<start>']], 0)

        predictions, state_out, hidden, _ = decoder(dec_input, features, state_out, hidden)
        predictions = tf.nn.softmax(predictions).numpy()
    
        init = self.find_n_best(predictions, beam_width)
        results = [[obj[0], obj[1], hidden, self.tokenizer.index_word[int(obj[1])] + " ", state_out] for obj in init]  # 0 - prob ; 1 - id ; 2 - hidden

        for i in range(self.max_length):
            tmp_res = []

            for r in results:
                tmp_preds, tmp_state_out, tmp_hidden, attention_plot = decoder(tf.expand_dims([r[1]], 0), features, r[4], r[2])
                
                for obj in self.find_n_best(tf.nn.softmax(tmp_preds).numpy(), beam_width):
                    tmp_res.append([obj[0] + r[0], obj[1], tmp_hidden, r[3] + self.tokenizer.index_word[int(obj[1])] + " ", tmp_state_out, attention_plot])  # multiplied scores, curr id, hidden, prev id 

            results.clear()
            tmp_res.sort(reverse=True, key=lambda x: x[0])
            # attention_plot[i] = tf.reshape(attention_weights, (-1,)).numpy()
            for el in range(beam_width):        
                results.append(tmp_res[el])
            
            for res, att in zip(results, attention_plots):
                att[i] = tf.reshape(res[5], (-1,)).numpy()

            if any(self.tokenizer.index_word[int(results[i][1])] == '<end>' for i in range(len(results))):
                break

            # if all(['<end>' in r[3] for r in results]):
            #     break


        # for el in results:
        #     tf.print(el[3] + "\n")
        # tf.print(results[0][3])
        #return [results[0][3]], None
        return [el[3] for el in results], None


    def beam_evaluate_2(self, image, decoder, encoder, beam_width=5):
        hidden = decoder.get_initial_state(batch_size=1, dtype="float32")
        state_out = hidden[0] 

        temp_input = tf.expand_dims(Training.load_image(image)[0], 0)

        dec_input = tf.expand_dims([self.tokenizer.word_index['<start>']], 0)

        features = encoder(temp_input)
        result = []
        for _ in range(self.max_length):
            ids = []

            for _ in range(beam_width):
                predictions, state_out, tmp_hidden, _ = decoder(dec_input, features, state_out, hidden)
                ids.append([tf.random.categorical(predictions, 1)[0][0].numpy(), max(tf.nn.softmax(predictions).numpy().tolist()[0]), tmp_hidden, state_out])  # predicted_id

                
            md = mode([id[0] for id in ids])
            tmp = []
            for el in ids:
                if el[0] == md:
                    tmp.append(el)
            best = max(el[1] for el in ids)
            # hidden = random.choice([h[2] for h in tmp])
            for el in tmp:
                if el[1] == best:
                    hidden = el[2]
                    state_out = el[3]
                    break


            result.append(self.tokenizer.index_word[md])

            if self.tokenizer.index_word[md] == '<end>':
                return result, None

            dec_input = tf.expand_dims([md], 0)
            #tf.print(hidden)

        return result, None

    

    def categorical_evaluate(self, image, decoder, encoder):
        global checkpoint_path
        attention_plot = np.zeros((self.max_length, 148))

        hidden = decoder.get_initial_state(batch_size=1, dtype="float32")
        state_out = hidden[0] 

        temp_input = tf.expand_dims(Training.load_image(image)[0], 0)
        # img_tensor_val = image_features_extract_model(temp_input)
        # img_tensor_val = tf.reshape(img_tensor_val, (img_tensor_val.shape[0],
        #                                             -1,
        #                                             img_tensor_val.shape[3]))

        features = encoder(temp_input)
        # hidden = hidden_enc

        dec_input = tf.expand_dims([self.tokenizer.word_index['<start>']], 0)
        result = []

        for i in range(self.max_length):
            
            predictions, state_out, hidden, attention_weights = decoder(dec_input,
                                                             features,
                                                             state_out, hidden)

            [print(f"{val} - {sorted(attention_weights[0].numpy().tolist(), reverse=True).index(val)}") for val in attention_weights[0].numpy().tolist()]
            print("---------------------")

            attention_plot[i] = tf.reshape(attention_weights, (-1,)).numpy()

            predicted_id = tf.random.categorical(predictions, 1)[0][0].numpy()
            result.append(self.tokenizer.index_word[predicted_id])

            if self.tokenizer.index_word[predicted_id] == '<end>':
                Training.plot_attention(image, result, attention_plot)
                return result, attention_plot

            dec_input = tf.expand_dims([predicted_id], 0)
            #tf.print(hidden)

        attention_plot = attention_plot[:len(result), :]
        
        return result, None

    def predict(self, decoder_type, image_path: str):
        global tokenizer_path, tokenizer_params_path, checkpoint_path
        try:
            with open(tokenizer_path, "r") as f:
                data = json.load(f)
                self.tokenizer = tokenizer_from_json(data)
            print("Tokenizer has been loaded")
            with open(tokenizer_params_path, "r") as txt:
                for line in txt:
                    regex = re.findall(r'\w+', line)
                    self.max_length = int(regex[0])
        except:
            raise IOError("Something went wrong with initializing tokenizer")

        encoder = CNN_Encoder(self.embedding_dim, m=10)
        decoder = RNN_Decoder(self.embedding_dim, self.units, self.vocab_size)
        optimizer = tf.keras.optimizers.Adam()

        ckpt = tf.train.Checkpoint(encoder=encoder,
                                   decoder=decoder, 
                                   optimizer=optimizer)
        ckpt_manager = tf.train.CheckpointManager(ckpt, checkpoint_path, max_to_keep=5)
        if ckpt_manager.latest_checkpoint:
            # restoring the latest checkpoint in checkpoint_path
            ckpt.restore(ckpt_manager.latest_checkpoint).expect_partial()
            print("Restored from {}".format(ckpt_manager.latest_checkpoint))
        else:
            print("Restored from scratch")

        if decoder_type == "categorical":
            result, attention_plot = self.categorical_evaluate(image_path, decoder, encoder)
        elif decoder_type == "beam":
            result, attention_plot = self.beam_evaluate(image_path, decoder, encoder, beam_width=2)
        elif decoder_type == "beam2":
            result, attention_plot = self.beam_evaluate_2(image_path, decoder, encoder, beam_width=5)
        else:
            raise IOError("decoder error")

        
        return result
        #print('Prediction Caption:', ' '.join(result))
        #Training.plot_attention(image_path, result, attention_plot)
        #print(f"len res = {len(result)}")
        # opening the image
        #Image.open(open(image_path, 'rb'))


class VAN:
    loaded = False
    d_p = "formula_images_png_5_large_resized\\"
    c_p = "5_dataset_large.json"
    top_k = 300
    image_count = 100000
    BATCH_SIZE = 64
    BUFFER_SIZE = 100
    embedding_dim = 200
    units = 200
    EPOCHS = 100
    conv_var = 9

    def __init__(self, model_name: str, working_path: str = ""):
        self.model_path = os.path.abspath(".") + "\\trained_models\\" + working_path + model_name
        self.init()

    def init(self):
        global tokenizer_path, tokenizer_params_path, checkpoint_path, meta_path
        tokenizer_path = self.model_path + "\\tokenizer.json"
        tokenizer_params_path = self.model_path + "\\tokenizer_params.txt"
        checkpoint_path = self.model_path + "\\checkpoints\\"
        meta_path = self.model_path + "\\meta.txt"

        if os.path.exists(checkpoint_path) and len(os.listdir(checkpoint_path)) != 0 and os.path.exists(tokenizer_path) \
                and os.path.exists(tokenizer_params_path) and os.path.exists(meta_path):
            print(f"Model has been found at {self.model_path}")
            self.loaded = True
        elif not os.path.exists(self.model_path):
            print(f"Model will be created at {self.model_path}")
        else:
            if input(f"Model is corrupted. Remove? (y/AB): ") == "y":
                shutil.rmtree(self.model_path)
                self.loaded = False
            else:
                self.loaded = True

    def get_model_path(self):
        return self.model_path

    def remove_temp(self):
        if not self.loaded:
            raise ValueError("Model is not loaded!")
        files = os.listdir(DATASET_PATH)
        for file in files:
            if file.split(".")[-1] == "npy":
                os.remove(DATASET_PATH + file)

    def input(self, inp, val):
        return val if inp == "" else inp

    def train(self):
        global DATASET_PATH, ANNOTATION_FILE

        print(f"Caption file must be in {os.path.abspath('.')}")
        print(f"Dataset folder must be in {os.path.abspath('.')}\\datasets\\")
        if self.loaded:
            if input("You will loose your model. Proceed? (y/AB): ") == "y":
                shutil.rmtree(self.model_path)
                self.loaded = False
            else:
                return
        if not self.loaded:
            print("\nPlease enter some data for new model: ")
            try:
                self.d_p = self.input(input(f"dataset_path - Default = {self.d_p}: "), self.d_p)
                self.c_p = self.input(input(f"caption file - Default = {self.c_p}: "), self.c_p)
                self.top_k = int(
                    self.input(input(f"top_k - Default = {self.top_k} (number of top used words in caps): "),
                               self.top_k))
                self.image_count = int(
                    self.input(input(f"image_count - Default = {self.image_count} (number of photos to be used): "),
                               self.image_count))
                self.BATCH_SIZE = int(self.input(input(f"BATCH_SIZE - Default = {self.BATCH_SIZE}: "), self.BATCH_SIZE))
                self.BUFFER_SIZE = int(
                    self.input(input(f"BUFFER_SIZE - Default = {self.BUFFER_SIZE}: "), self.BUFFER_SIZE))
                self.embedding_dim = int(
                    self.input(input(f"embedding_dim - Default = {self.embedding_dim}: "), self.embedding_dim))
                self.units = int(self.input(input(f"units - Default = {self.units}: "), self.units))
                self.EPOCHS = int(self.input(input(f"EPOCHS - Default = {self.EPOCHS}: "), self.EPOCHS))
                self.conv_var = int(self.input(input(f"conv_var - Default = {self.conv_var}: "), self.conv_var))
            except:
                raise TypeError("Model params initialization failed")

            self.loaded = True
            DATASET_PATH = os.path.abspath(".") + "\\datasets\\" + self.d_p
            ANNOTATION_FILE = os.path.abspath(".") + "\\" + self.c_p

            train = Training(manager=self,
                             top_k=self.top_k,
                             image_count=self.image_count,
                             BATCH_SIZE=self.BATCH_SIZE,
                             BUFFER_SIZE=self.BUFFER_SIZE,
                             embedding_dim=self.embedding_dim,
                             units=self.units,
                             EPOCHS=self.EPOCHS,
                             conv_var=self.conv_var)

            train.auto_train()

    def predict(self, decoder, image_path: str):
        if not self.loaded:
            raise ValueError("Model is not loaded!")
        pred = Prediction()
        res = pred.predict(decoder, image_path)
        if decoder == "categorical" or decoder == "beam2" or decoder == "beam3":
            print(' '.join(res))
        if decoder == "beam":
            [print(r + "\n") for r in res]


    def random_predict(self, dataset_path, caption_path, number=9):
        if not self.loaded:
            raise ValueError("Model is not loaded!")
        with open(caption_path, 'r+') as file:
            capt = json.load(file)["annotations"]

        parameters = {'axes.labelsize': 10,
          'axes.titlesize': 10}
        plt.rcParams.update(parameters)

        pred = Prediction()
        images = random.choices(capt, k=number)
        plotting = []
        for im in images:
            plotting.append([im["caption"], pred.predict("beam", dataset_path + im["image_id"] + ".png"), plt.imread(dataset_path + im["image_id"] + ".png")])  # real ; pred ; plt image

        fig, axes = plt.subplots(nrows=5, ncols=1)

        for ax, plot in zip(axes.flat, plotting):
            ax.imshow(plot[2])
            ax.set(title=f"real = {plot[0]}\npred = {plot[1][0]}")
            ax.axis('off')
        plt.show()

        
            
        
        


# physical_devices = tf.config.list_physical_devices('GPU')
# tf.config.experimental.set_memory_growth(physical_devices[0], True)
# tf.data.experimental.enable_debug_mode()

enable_gpu(False, gb=9)
van = VAN("model_latex_x14")

van.train()

# van.random_predict("C:\\Users\\shace\\Documents\\GitHub\\im2latex\\datasets\\formula_images_png_5_large_resized\\", 
#                     "C:\\Users\\shace\\Documents\\GitHub\\im2latex\\5_dataset_large.json", 5)
van.predict("categorical", "C:/Users/shace/Desktop/eval/dopfeq.png")
