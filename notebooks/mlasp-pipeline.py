import os

import kfp

#import kfp_tekton
import pandas as pd

from typing import NamedTuple

os.environ["DEFAULT_STORAGE_CLASS"] = "gp3-csi" #get this from your OCP Storage Classes
os.environ["DEFAULT_ACCESSMODES"] = "ReadWriteOnce"

aws_access_key_id = os.environ["AWS_ACCESS_KEY_ID"]
aws_secret_access_key = os.environ["AWS_SECRET_ACCESS_KEY"]
endpoint_url = os.environ["AWS_S3_ENDPOINT"]
bucket_name = os.environ["AWS_S3_BUCKET"]
region_name = os.environ["AWS_DEFAULT_REGION"]    

aws_info = {"aws_access_key_id":aws_access_key_id, 
            "aws_secret_access_key":aws_secret_access_key, 
            "endpoint_url":endpoint_url,
            "bucket_name":bucket_name,
            "region_name":region_name
           }

def data_prep(X_train_file: kfp.components.OutputPath(),
              y_train_file: kfp.components.OutputPath(),
              aws_info: dict):    
    import pandas as pd
    import os
    import botocore
    import boto3
    from sklearn.model_selection import train_test_split
    import pickle
        
    key = "data/lt_results_2022-10-01.csv"

    data = pd.read_csv(
        f"s3://{aws_info['bucket_name']}/{key}",
        storage_options={
            "key": aws_info["aws_access_key_id"],
            "secret": aws_info["aws_secret_access_key"],
            "endpoint_url": aws_info["endpoint_url"],            
        },
        index_col='DateTime', 
        parse_dates=True, 
        infer_datetime_format=True,
    )
    print('Loaded data into pandas df.')
    
    data = data.drop(columns=['req2xx', 'testDurationSeconds'])
    X_train, X_test, y_train, y_test = train_test_split(data, data.mean_tps,
                                                        test_size=0.1,
                                                        random_state=0)
    print('Train-test split completed.')
    
    target_var = 'mean_tps'
    X_train = X_train.drop(target_var, axis=1)
    X_test = X_test.drop(target_var, axis=1)
    
    from sklearn.preprocessing import StandardScaler
    stdScaler = StandardScaler()
    targetStdScaler = StandardScaler()
    X_train_scaled = stdScaler.fit_transform(X_train.values)
    y_train_scaled = targetStdScaler.fit_transform(y_train.values.reshape(-1,1))
    #X_test_scaled = stdScaler.transform(X_test.values)
    #y_test_scaled = targetStdScaler.transform(y_test.values.reshape(-1,1))
    
    print('Stdandard scaling completed.')
        
    def save_pickle(object_file, target_object):
        with open(object_file, "wb") as f:
            pickle.dump(target_object, f)
            
    save_pickle(X_train_file, X_train_scaled)
    #save_pickle(X_test_file, X_test_scaled)
    save_pickle(y_train_file, y_train_scaled)
    #save_pickle(y_test_file, y_test_scaled)
    print('Data saved for next stage')


def prepare_model(X_train_file: kfp.components.InputPath(),
                  y_train_file: kfp.components.InputPath(),
                  aws_info:dict,
                 ):
    
    import pandas as pd
    import os
    import botocore
    import boto3
    import pickle
    
    
    # Neural Nets imports
    from tensorflow.keras.models import Sequential, load_model, save_model
    from tensorflow.keras.layers import Dense, Dropout, BatchNormalization 
    from tensorflow.keras.optimizers import Adam
    from tensorflow.keras.callbacks import ReduceLROnPlateau, ModelCheckpoint

    def load_pickle(object_file):
        with open(object_file, "rb") as f:
            target_object = pickle.load(f)

        return target_object

    X_train = load_pickle(X_train_file)
    y_train = load_pickle(y_train_file)

    verboseLevel=0
    validationSplit=0.2
    batchSize=30
    epochs=1000
    layerSize=64
    inputSize = X_train.shape[1]

    # callback preparation
    reduce_lr = ReduceLROnPlateau(monitor='val_loss',
                                  factor=0.5,
                                  patience=2,
                                  verbose=verboseLevel,
                                  mode='min',
                                  min_lr=0.001)

    target_loss = 'mae'
    measure_metrics = ['mae', 'mse']

    model = Sequential()
    model.add(Dense(layerSize, kernel_initializer='normal',
                    input_dim=inputSize, activation='relu'))
    for j in range(4):
        model.add(Dense(layerSize, 
                        kernel_initializer='normal', activation='relu'))
    model.add(BatchNormalization())
    model.add(Dense(1, kernel_initializer='normal', 
                    activation='linear'))

    optmzr=Adam(learning_rate=0.001)    
    model.compile(optimizer=optmzr, loss=target_loss, metrics=measure_metrics)

    model_h5_name = 'mlp_' + str(layerSize)+ '_' + str(4) + '_model_std_' + 'pipeline' + '.h5'
    checkpoint_nn_std = ModelCheckpoint(model_h5_name,
                             monitor='val_loss',
                             verbose=verboseLevel,
                             save_best_only=True,
                             mode='min')
    callbacks_list_nn_std = [checkpoint_nn_std, reduce_lr]
    print("Model defined, starting training...")

    model.fit(X_train, y_train,
              batch_size=batchSize, 
              validation_split=validationSplit, 
              epochs=epochs, verbose=verboseLevel,
              callbacks=callbacks_list_nn_std)

    model_new = load_model(model_h5_name)
    
    print("Model training completed. Preparing export...")
    
    import tf2onnx
    model_onnx, _ = tf2onnx.convert.from_keras(model_new, output_path='tf_mlasp.onnx')
    
    s3_odf = boto3.client(service_name = 's3',
                      aws_access_key_id = aws_info["aws_access_key_id"],
                      aws_secret_access_key = aws_info["aws_secret_access_key"],
                      region_name = aws_info["region_name"],
                      endpoint_url = aws_info["endpoint_url"],
                      config = botocore.client.Config(signature_version = 's3'))
    
    import pytz
    from datetime import timedelta, datetime
    local_tz = pytz.timezone('America/Toronto')
    now=datetime.now(local_tz).strftime('%Y-%m-%d_%H-%M-%S')
    model_folder = 'model_' + now

    
    print(f'Model folder defined:{model_folder}.')
    
    model_target = model_folder+'/tf_mlasp.onnx'
    s3_odf.upload_file('tf_mlasp.onnx', aws_info["bucket_name"], model_target)
    
    print(f'Model uploaded to bucket:{aws_info["bucket_name"]}.')


data_prep_op = kfp.components.create_component_from_func(data_prep,
                                                         base_image="image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/tensorflow:2023.1",
                                                         packages_to_install=["s3fs"],
                                                        )


prepare_model_op = kfp.components.create_component_from_func(prepare_model,
                                                             base_image="image-registry.openshift-image-registry.svc:5000/redhat-ods-applications/tensorflow:2023.1",
                                                             #packages_to_install=["s3fs"],
)


@kfp.dsl.pipeline(name="MLASP Pipeline")
def mlasp_pipeline(model_obc: str = "mlasp-model"):
    data_prep_task = data_prep_op(aws_info)
    
    prepare_model_task = prepare_model_op(data_prep_task.outputs["X_train"], 
                                          data_prep_task.outputs["y_train"], 
                                          aws_info
                                       )

    

from kfp_tekton.compiler import TektonCompiler

if __name__ == "__main__":
    
    # There are 2 options presented here.
    # First option is connecting directly to the DS Pipelines backend and creates a pipeline run directly from this code
    '''
    print(f"Connecting to kfp: {kubeflow_endpoint}")
    client = kfp_tekton.TektonClient(
        host=kubeflow_endpoint,
        existing_token=bearer_token,
    )
    result = client.create_run_from_pipeline_func(
        mlasp_pipeline, arguments={}, experiment_name="mlasp"
    )
    print(f"Starting pipeline run with run_id: {result.run_id}")
    '''
    
    #The second option is to compile the pipeline into YAML and deploy it using the UI
    print("Please wait while the pipeline is compiling...\n")
    TektonCompiler().compile(mlasp_pipeline, package_path="mlasp_pipeline.yaml")
    print("Pipeline compiled!")



