# Learning Rolling Shutter Correction from Real Data without Camera Motion Assumption
# Copyright (C) <2020> <Jiawei Mo, Md Jahidul Islam, Junaed Sattar>

# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.

# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.

# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <https://www.gnu.org/licenses/>.

from __future__ import absolute_import, division, print_function
from keras.models import Input, Model
from keras.layers import Conv2D, Conv2DTranspose, BatchNormalization, Activation, Concatenate, UpSampling2D
import tensorflow as tf


def iconv_pr(input, pr_prv, conv, filters, lvl):
    upconv = Conv2DTranspose(
        filters, kernel_size=4, strides=2, padding='same', name='upconv'+str(lvl))(input)
    upconv = Activation('relu')(BatchNormalization(
        axis=3, name='upconv{}bn'.format(lvl))(upconv))
    pr_prv_upsampled = UpSampling2D(name='prupsample'+str(lvl))(pr_prv)
    upconv_prprv_conv = Concatenate(axis=3)([upconv, pr_prv_upsampled, conv])
    iconv = Activation('relu')(Conv2D(filters, kernel_size=3, strides=1,
                                      padding='same', name='iconv'+str(lvl))(upconv_prprv_conv))
    pr = Activation('relu')(Conv2D(1, kernel_size=3, strides=1,
                                   padding='same', name='pr'+str(lvl))(iconv))
    return [iconv, pr]


def DispNet(img_input):
    # encoder
    conv1 = Activation('relu')(
        Conv2D(64, kernel_size=7, strides=2, padding='same', name='conv1')(img_input))
    conv2 = Activation('relu')(
        Conv2D(128, kernel_size=5, strides=2, padding='same', name='conv2')(conv1))
    conv3a = Activation('relu')(
        Conv2D(256, kernel_size=5, strides=2, padding='same', name='conv3a')(conv2))
    conv3b = Activation('relu')(
        Conv2D(256, kernel_size=3, strides=1, padding='same', name='conv3b')(conv3a))
    conv4a = Activation('relu')(
        Conv2D(512, kernel_size=3, strides=2, padding='same', name='conv4a')(conv3b))
    conv4b = Activation('relu')(
        Conv2D(512, kernel_size=3, strides=1, padding='same', name='conv4b')(conv4a))
    conv5a = Activation('relu')(
        Conv2D(512, kernel_size=3, strides=2, padding='same', name='conv5a')(conv4b))
    conv5b = Activation('relu')(
        Conv2D(512, kernel_size=3, strides=1, padding='same', name='conv5b')(conv5a))
    conv6a = Activation('relu')(
        Conv2D(1024, kernel_size=3, strides=2, padding='same', name='conv6a')(conv5b))
    conv6b = Activation('relu')(
        Conv2D(1024, kernel_size=3, strides=1, padding='same', name='conv6b')(conv6a))

    pr6 = Activation('relu')(
        Conv2D(1, kernel_size=3, strides=1, padding='same', name='pr6')(conv6a))

    # decoder
    [iconv5, pr5] = iconv_pr(conv6b, pr6, conv5b, 512, 5)
    [iconv4, pr4] = iconv_pr(iconv5, pr5, conv4b, 256, 4)
    [iconv3, pr3] = iconv_pr(iconv4, pr4, conv3b, 128, 3)
    [iconv2, pr2] = iconv_pr(iconv3, pr3, conv2, 64, 2)
    [iconv1, pr1] = iconv_pr(iconv2, pr2, conv1, 32, 1)

    return [pr6, pr5, pr4, pr3, pr2, pr1]


class DepthNet():
    def __init__(self, im_shape):
        img = Input(shape=(im_shape[0], im_shape[1], 1))
        [pr6, pr5, pr4, pr3, pr2, pr1] = DispNet(img)
        depth = UpSampling2D(name='y_pred')(pr1)
        self.model = Model(input=img, output=depth)

    def depthLoss(self, y_true, y_pred):
        diff = tf.where(tf.is_nan(y_true),
                        tf.zeros_like(y_true), y_true-y_pred)
        mean = tf.sqrt(tf.reduce_mean(tf.square(diff)))
        return mean
