import pandas as pd
import numpy as np
import tensorflow as tf
import tensorflow_hub as hub
import tensorflow_text as text
from official.nlp import optimization
import tensorflow_addons as tfa
from sklearn.metrics import f1_score

for device in tf.config.list_physical_devices():
    print(": {}".format(device.name))

df1 = pd.read_csv("/content/SQLiV3.csv", encoding = 'utf-8')
df1 = df1[["Sentence","Label"]]

df2 = pd.read_csv("/content/sqli.csv", encoding = 'utf-16')
df3 = pd.read_csv("/content/sqliv2.csv", encoding = 'utf-16')

df = pd.concat([df1,df2,df3])
df.dropna(inplace = True)

df = df[(df['Label'] == "0") | (df['Label'] == "1")]
df = df.drop_duplicates(subset = 'Sentence')
df["Label"] = pd.to_numeric(df["Label"])

df = df.sample(frac = 1).reset_index(drop = True)
df.rename(columns = {'Sentence' : 'X', 'Label' : 'y'}, inplace = True)

slice_index_1 = int(0.8*len(df))
slice_index_2 = int(0.9*len(df))
train_df = df.iloc[:slice_index_1, :]
val_df = df.iloc[slice_index_1:slice_index_2, :]
test_df = df.iloc[slice_index_2:,:]

X_train = train_df
y_train = X_train.pop('y').to_frame()

X_val = val_df
y_val = X_val.pop('y').to_frame()

X_test = test_df
y_test = X_test.pop('y').to_frame()

train_ds = tf.data.Dataset.from_tensor_slices((X_train,y_train))
val_ds = tf.data.Dataset.from_tensor_slices((X_val,y_val))
test_ds = tf.data.Dataset.from_tensor_slices((X_test,y_test))

print(train_ds)
print(len(list(train_ds)))
print(val_ds)
print(len(list(val_ds)))
print(test_ds)
print(len(list(test_ds)))

test_text = ["this is a test"]

def build_classifier_model():
    text_input = tf.keras.layers.Input(shape = (),dtype = tf.string, name = 'text')
    preprocessing_layer = hub.KerasLayer("https://tfhub.dev/tensorflow/bert_en_uncased_preprocess/3", name = 'preprocessing')
    encoder_inputs = preprocessing_layer(text_input)
    encoder = hub.KerasLayer("https://tfhub.dev/google/electra_small/2", trainable=True, name = 'Electra_encoder')
    outputs = encoder(encoder_inputs)
    net = outputs['pooled_output']
    net = tf.keras.layers.Dropout(0.1)(net)
    net = tf.keras.layers.Dense(1, activation = None, name = 'classifier')(net)
    return tf.keras.Model(text_input, net)

classifier_model = build_classifier_model()
bert_raw_result = classifier_model(tf.constant(test_text))

print(tf.sigmoid(bert_raw_result))

tf.keras.utils.plot_model(classifier_model)

loss = tf.keras.losses.BinaryCrossentropy(from_logits = True)
metrics = tf.metrics.BinaryAccuracy()

epochs = 1
steps_per_epoch = tf.data.experimental.cardinality(train_ds).numpy()
num_train_steps = steps_per_epoch * epochs
num_warmup_steps = int(0.1 * num_train_steps)

init_lr = 3e-5
optimizer = optimization.create_optimizer(init_lr = init_lr, num_train_steps = num_train_steps,
                                         num_warmup_steps = num_warmup_steps, optimizer_type = 'adamw')

classifier_model.compile(optimizer = optimizer, loss = loss, metrics = metrics)

history = classifier_model.fit(x=train_ds, validation_data = val_ds, epochs = epochs,verbose =1)

score = classifier_model.evaluate(test_ds)

y_pred = classifier_model.predict(test_ds)

for i in range(len(y_pred)):
    if y_pred[i] >= 0.5:
        y_pred[i] = 1
    else:
        y_pred[i] = 0

print("")
print(f"Accuracy of ELECTRA on test set : {score[1]}")
print(f"F1 Score of ELECTRA on test set : {f1_score(y_test, y_pred)}")

