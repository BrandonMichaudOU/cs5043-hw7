'''
Advanced Machine Learning, 2024
HW 5 Base Code

Author: Andrew H. Fagg (andrewhfagg@gmail.com)

Image classification for the Core 50 data set

Updates for using caching and GPUs
- Batch file:
#SBATCH --gres=gpu:1
#SBATCH --partition=gpu
or
#SBATCH --partition=disc_dual_a100_students
#SBATCH --cpus-per-task=64

- Command line options to include
--cache $LSCRATCH                              (use lscratch to cache the datasets to local fast disk)
--batch 4096                                   (this parameter is per GPU)
--gpu
--precache datasets_by_fold_4_objects          (use a 4-object pre-constructed dataset)

Notes: 
- batch is now a parameter per GPU.  If there are two GPUs, then this number is doubled internally.
   Note that you must do other things to make use of more than one GPU
- 4096 works on the a100 GPUs
- The prcached dataset is a serialized copy of a set of TF.Datasets (located on slow spinning disk).  
Each directory contains all of the images for a single data fold within a couple of files.  Loading 
these files is *a lot* less expensive than having to load the individual images and preprocess them 
at the beginning of a run.
- The cache is used to to store the loaded datasets onto fast, local SSD so they can be fetched quickly
for each training epoch

'''

import sys
import argparse
import pickle
import pandas as pd
import wandb
import socket
import tensorflow as tf
import matplotlib.pyplot as plt

from tensorflow.keras.utils import plot_model
from tensorflow import keras

# Provided
from chesapeake_loader import *
from hw7_parser import *
from gan import *
from gan_train_loop import *


def generate_fname(args):
    '''
    Generate the base file name for output files/directories.
    
    The approach is to encode the key experimental parameters in the file name.  This
    way, they are unique and easy to identify after the fact.

    :param args: from argParse
    :params_str: String generated by the JobIterator
    '''
    return f'{args.results_path}/{args.exp_type}'


def execute_exp(args=None, multi_gpus=False):
    '''
    Perform the training and evaluation for a single model
    
    :param args: Argparse arguments
    :param multi_gpus: True if there are more than one GPU
    '''

    # Check the arguments
    if args is None:
        # Case where no args are given (usually, because we are calling from within Jupyter)
        #  In this situation, we just use the default arguments
        parser = create_parser()
        args = parser.parse_args([])

    print(args.exp_index)

    # Scale the batch size with the number of GPUs
    if multi_gpus > 1:
        args.batch = args.batch * multi_gpus

    print('Batch size', args.batch)

    ####################################################
    # Create the TF datasets for training, validation, testing

    if args.verbose >= 3:
        print('Starting data flow')

    # Load individual files (all objects)
    if not args.no_data:
        ds_train, ds_valid, ds_test, num_classes = create_datasets(base_dir=args.dataset,
                                                                   full_sat=False,
                                                                   patch_size=args.image_size,
                                                                   fold=args.fold,
                                                                   cache_dir=args.cache,
                                                                   repeat_train=args.repeat,
                                                                   shuffle_train=args.shuffle,
                                                                   batch_size=args.batch,
                                                                   prefetch=args.prefetch,
                                                                   num_parallel_calls=args.num_parallel_calls)
    else:
        ds_train, ds_valid, ds_test, num_classes = None, None, None, 7

    # Build the model
    if args.verbose >= 3:
        print('Building network')

    # Create the network
    if multi_gpus > 1:
        # Multiple GPUs
        mirrored_strategy = tf.distribute.MirroredStrategy()

        with mirrored_strategy.scope():
            # Build network: you must provide your own implementation
            d, g, meta = create_gan(image_size=(args.image_size, args.image_size),
                                    n_channels=3,
                                    n_classes=num_classes,
                                    d_filters=args.d_filters,
                                    d_hidden=args.d_hidden,
                                    g_n_noise_steps=args.g_n_noise_steps,
                                    g_filters=args.g_filters,
                                    d_n_conv_per_step=args.d_n_conv_per_step,
                                    d_conv_activation=args.d_conv_activation,
                                    d_kernel_size=args.d_kernel_size,
                                    d_padding=args.d_padding,
                                    d_sdropout=args.d_sdropout,
                                    d_dense_activation=args.d_dense_activation,
                                    d_dropout=args.d_dropout,
                                    d_batch_normalization=args.d_batch_normalization,
                                    d_lrate=args.d_lrate,
                                    d_loss=tf.keras.losses.BinaryCrossentropy(),
                                    d_metrics=[tf.keras.metrics.BinaryAccuracy()],
                                    g_n_conv_per_step=args.g_n_conv_per_step,
                                    g_conv_activation=args.g_conv_activation,
                                    g_kernel_size=args.g_kernel_size,
                                    g_padding=args.g_padding,
                                    g_sdropout=args.g_sdropout,
                                    g_batch_normalization=args.g_batch_normalization,
                                    m_lrate=args.m_lrate,
                                    m_loss=tf.keras.losses.BinaryCrossentropy(),
                                    m_metrics=[tf.keras.metrics.BinaryAccuracy()])
    else:
        # Single GPU
        # Build network: you must provide your own implementation
        d, g, meta = create_gan(image_size=(args.image_size, args.image_size),
                                n_channels=3,
                                n_classes=num_classes,
                                d_filters=args.d_filters,
                                d_hidden=args.d_hidden,
                                g_n_noise_steps=args.g_n_noise_steps,
                                g_filters=args.g_filters,
                                d_n_conv_per_step=args.d_n_conv_per_step,
                                d_conv_activation=args.d_conv_activation,
                                d_kernel_size=args.d_kernel_size,
                                d_padding=args.d_padding,
                                d_sdropout=args.d_sdropout,
                                d_dense_activation=args.d_dense_activation,
                                d_dropout=args.d_dropout,
                                d_batch_normalization=args.d_batch_normalization,
                                d_lrate=args.d_lrate,
                                d_loss=tf.keras.losses.BinaryCrossentropy(),
                                d_metrics=[tf.keras.metrics.BinaryAccuracy()],
                                g_n_conv_per_step=args.g_n_conv_per_step,
                                g_conv_activation=args.g_conv_activation,
                                g_kernel_size=args.g_kernel_size,
                                g_padding=args.g_padding,
                                g_sdropout=args.g_sdropout,
                                g_batch_normalization=args.g_batch_normalization,
                                m_lrate=args.m_lrate,
                                m_loss=tf.keras.losses.BinaryCrossentropy(),
                                m_metrics=[tf.keras.metrics.BinaryAccuracy()])

    # Report model structure if verbosity is turned on
    if args.verbose >= 1:
        print(d.summary())
        print('\n\n\n')
        print(g.summary())
        print('\n\n\n')
        print(meta.summary())
        print('\n\n\n')

    print(args)

    # Output file base and pkl file
    fbase = generate_fname(args)
    print(fbase)
    fname_out = "%s_results.pkl" % fbase

    # Plot the model
    if args.render:
        plot_model(d, to_file=f'{fbase}_discriminator_plot.png', show_shapes=True, show_layer_names=True)
        plot_model(g, to_file=f'{fbase}_generator_plot.png', show_shapes=True, show_layer_names=True)
        plot_model(meta, to_file=f'{fbase}_meta_plot.png', show_shapes=True, show_layer_names=True)

    # Perform the experiment?
    if args.nogo:
        # No!
        print("NO GO")
        print(fbase)
        return

    # Check if output file already exists
    if not args.force and os.path.exists(fname_out):
        # Results file does exist: exit
        print("File %s already exists" % fname_out)
        return

    #####
    # Start wandb
    # run = wandb.init(project=args.project, name='%s_R%d' % (args.label, args.rotation), notes=fbase, config=vars(args))
    #
    # # Log hostname
    # wandb.log({'hostname': socket.gethostname()})
    #
    # # Callbacks
    # cbs = []
    # early_stopping_cb = keras.callbacks.EarlyStopping(patience=args.patience, restore_best_weights=True,
    #                                                   min_delta=args.min_delta, monitor=args.monitor)
    # cbs.append(early_stopping_cb)
    #
    # # Weights and Biases
    # wandb_metrics_cb = wandb.keras.WandbMetricsLogger()
    # cbs.append(wandb_metrics_cb)

    if args.verbose >= 3:
        print('Fitting model')

    # Learn
    L_fake, I_fake, I_fake_no_use = train_loop(g_model=g,
                                               d_model=d,
                                               gtrain_model=meta,
                                               ds_train=ds_train,
                                               n_noise_steps=args.g_n_noise_steps,
                                               image_size=args.image_size,
                                               nepochs_meta=args.nepochs_meta,
                                               nepochs_d=args.nepochs_d,
                                               nepochs_g=args.nepochs_g,
                                               verbose=args.verbose >= 2)

    fig = render_examples(L_fake, I_fake, I_fake_no_use)
    fig.savefig('figures/examples.png')

    # Done training

    # # Generate results data
    # results = {}
    #
    # # Test set
    # if ds_test is not None:
    #     print('#################')
    #     print('Testing')
    #     results['predict_testing_eval'] = model.evaluate(ds_test)
    #     wandb.log({'final_test_loss': results['predict_testing_eval'][0]})
    #     wandb.log({'final_test_sparse_categorical_accuracy': results['predict_testing_eval'][1]})
    #
    # # Save results
    # fbase = generate_fname(args, args_str)
    # results['fname_base'] = fbase
    # with open("%s_results.pkl" % (fbase), "wb") as fp:
    #     pickle.dump(results, fp)

    # Save model
    if args.save_model:
        d.save("%s_discriminator" % (fbase))
        g.save("%s_generator" % (fbase))
        meta.save("%s_meta" % (fbase))

    # wandb.finish()


if __name__ == "__main__":
    # Parse and check incoming arguments
    parser = create_parser()
    args = parser.parse_args()

    # n_physical_devices = 0

    if args.verbose >= 3:
        print('Arguments parsed')

    # Turn off GPU?
    if not args.gpu or "CUDA_VISIBLE_DEVICES" not in os.environ.keys():
        tf.config.set_visible_devices([], 'GPU')
        print('NO VISIBLE DEVICES!!!!')

    # GPU check
    visible_devices = tf.config.get_visible_devices('GPU')
    n_visible_devices = len(visible_devices)
    print('GPUS:', visible_devices)
    if n_visible_devices > 0:
        for device in visible_devices:
            tf.config.experimental.set_memory_growth(device, True)
        print('We have %d GPUs\n' % n_visible_devices)
    else:
        print('NO GPU')

    if args.cpus_per_task is not None:
        tf.config.threading.set_intra_op_parallelism_threads(args.cpus_per_task)
        tf.config.threading.set_inter_op_parallelism_threads(args.cpus_per_task)

    execute_exp(args, multi_gpus=n_visible_devices)
