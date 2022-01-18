"""Detection model evaluator.

This runs the DetectionModel evaluator.
"""

import argparse
import os

import tensorflow as tf

import avod
import avod.builders.config_builder_util as config_builder
from avod.builders.dataset_builder import DatasetBuilder
from avod.core.models.avod_model import AvodModel
from avod.core.models.rpn_model import RpnModel
from avod.core.evaluator import Evaluator

tf.logging.set_verbosity(tf.logging.ERROR)

def evaluate(model_config, eval_config, dataset_config, output_dir=None):

    # Parse eval config
    eval_mode = eval_config.eval_mode
    if eval_mode not in ['val', 'test']:
        raise ValueError('Evaluation mode can only be set to `val` or `test`')
    evaluate_repeatedly = eval_config.evaluate_repeatedly

    # Parse dataset config
    data_split = dataset_config.data_split
    if data_split == 'train':
        dataset_config.data_split_dir = 'training'
        dataset_config.has_labels = True

    elif data_split.startswith('val'):
        dataset_config.data_split_dir = 'training'

        # Don't load labels for val split when running in test mode
        if eval_mode == 'val':
            dataset_config.has_labels = True
        elif eval_mode == 'test':
            dataset_config.has_labels = False

    elif data_split == 'test':
        dataset_config.data_split_dir = 'testing'
        dataset_config.has_labels = False

    else:
        raise ValueError('Invalid data split', data_split)

    # Convert to object to overwrite repeated fields
    dataset_config = config_builder.proto_to_obj(dataset_config)

    # Remove augmentation during evaluation
    dataset_config.aug_list = []

    # Build the dataset object
    dataset = DatasetBuilder.build_kitti_dataset(dataset_config,
                                                 use_defaults=False)

    # Setup the model
    model_name = model_config.model_name

    # Convert to object to overwrite repeated fields
    model_config = config_builder.proto_to_obj(model_config)

    # Switch path drop off during evaluation
    model_config.path_drop_probabilities = [1.0, 1.0]

    with tf.Graph().as_default():
        if model_name == 'avod_model':
            model = AvodModel(model_config, train_val_test=eval_mode,
                              dataset=dataset)
        elif model_name == 'rpn_model':
            model = RpnModel(model_config, train_val_test=eval_mode,
                             dataset=dataset)
        else:
            raise ValueError('Invalid model name {}'.format(model_name))

        model_evaluator = Evaluator(model,
                                    dataset_config,
                                    eval_config,
                                    output_dir=output_dir)

        if evaluate_repeatedly:
            model_evaluator.repeated_checkpoint_run()
        else:
            model_evaluator.run_latest_checkpoints()


def main(_):
    parser = argparse.ArgumentParser()

    default_pipeline_config_path = avod.root_dir() + \
        '/configs/avod_cars_example.config'

    default_output_dir = '/data/kitti_avod/object/outputs'

    parser.add_argument('--pipeline_config',
                        type=str,
                        dest='pipeline_config_path',
                        default=default_pipeline_config_path,
                        help='Path to the pipeline config')

    parser.add_argument('--data_split',
                        type=str,
                        dest='data_split',
                        default='val',
                        help='Data split for evaluation')

    parser.add_argument('--device',
                        type=str,
                        dest='device',
                        default=None,
                        help='CUDA device id')

    parser.add_argument('--output_dir',
                        type=str,
                        dest='output_dir',
                        default=default_output_dir,
                        help='output dir to save checkpoints')

    args = parser.parse_args()

    # Parse pipeline config
    model_config, _, eval_config, dataset_config = \
        config_builder.get_configs_from_pipeline_file(
            args.pipeline_config_path,
            is_training=False,
            output_dir=args.output_dir)

    # Overwrite data split
    dataset_config.data_split = args.data_split

    # Set CUDA device id
    if args.device:
        os.environ['CUDA_VISIBLE_DEVICES'] = args.device

    evaluate(model_config, eval_config, dataset_config,
             output_dir=args.output_dir)


if __name__ == '__main__':
    tf.app.run()
