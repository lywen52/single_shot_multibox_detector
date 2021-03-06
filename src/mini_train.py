from keras.callbacks import ModelCheckpoint
from keras.callbacks import ReduceLROnPlateau
from keras.metrics import categorical_accuracy
from keras.optimizers import Adam
from keras.utils.visualize_util import plot

from image_generator import ImageGenerator
from multibox_loss import MultiboxLoss
from mini_models import mini_SSD300
from utils.prior_box_creator import PriorBoxCreator
from utils.prior_box_manager import PriorBoxManager
from utils.XML_parser import XMLParser
from utils.utils import split_data

# constants
batch_size = 10
num_epochs = 15
classes=['chair', 'bottle', 'sofa', 'tvmonitor', 'diningtable']
num_classes = len(classes) + 1
root_prefix = '../datasets/VOCdevkit/VOC2007/'
ground_data_prefix = root_prefix + 'Annotations/'
image_prefix = root_prefix + 'JPEGImages/'
image_shape = (300, 300 ,3)
model = mini_SSD300(image_shape, num_classes=num_classes)
plot(model, to_file='mini_SSD300.png')

def class_accuracy(y_true, y_pred):
    y_pred_classification = y_pred[:, :, 4:(4 + num_classes)]
    y_true_classification = y_true[:, :, 4:(4 + num_classes)]
    return categorical_accuracy(y_true_classification, y_pred_classification)

multibox_loss = MultiboxLoss(num_classes, neg_pos_ratio=2.0).compute_loss
model.compile(optimizer=Adam(lr=3e-4), loss=multibox_loss,
                                metrics=[class_accuracy])
box_creator = PriorBoxCreator(model)
prior_boxes = box_creator.create_boxes()
ground_truth_manager = XMLParser(ground_data_prefix, background_id=None,
                                                    class_names=classes)
ground_truth_data = ground_truth_manager.get_data()
print('Number of ground truth samples:', len(ground_truth_data.keys()))
train_keys, validation_keys = split_data(ground_truth_data, training_ratio=.8)

prior_box_manager = PriorBoxManager(prior_boxes,
                                    box_scale_factors=[.1, .1, .2, .2],
                                    num_classes=num_classes)

image_generator = ImageGenerator(ground_truth_data,
                                 prior_box_manager,
                                 batch_size,
                                 image_shape[0:2],
                                 train_keys, validation_keys,
                                 image_prefix,
                                 vertical_flip_probability=0,
                                 horizontal_flip_probability=0.5)


model_names = ('../trained_models/model_checkpoints/' +
               'weights.{epoch:02d}-{val_loss:.2f}.hdf5')
model_checkpoint = ModelCheckpoint(model_names,
                                   monitor='val_loss',
                                   verbose=1,
                                   save_best_only=False,
                                   save_weights_only=True)
learning_rate_schedule = ReduceLROnPlateau(monitor='val_loss', factor=0.1,
                                           patience=10, verbose=1, cooldown=20)

model.fit_generator(image_generator.flow(mode='train'),
                    len(train_keys),
                    num_epochs,
                    callbacks=[model_checkpoint, learning_rate_schedule],
                    validation_data=image_generator.flow(mode='val'),
                    nb_val_samples = len(validation_keys))
