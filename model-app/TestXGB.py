import pandas as pd
import joblib
import xgboost as xgb

class TestXGB(object):
  def __init__(self):
    self.model = joblib.load("xgbModel.pkl")
    self.features = ['asyncResp', 'asyncRespThreads', 'cThreads', 'jacptQSize', 'jacptThreads', 'ltTargetSize', 'numConnections', 'timeoutSeconds']


  def predict(self, X, features_names):
    print(f'Got X={X} of type {type(X)}, feature_names={self.features} \\n')
    record = pd.DataFrame(X, columns=self.features)
    print(f'Record is {record}')

    resp = 0
    try:
      resp = self.model.predict(record)
    except Exception as e:
        ex = e
        print(f"Prediction service exception: {ex}")
    
    return resp


  def metrics(self):
    return [
      {"type": "COUNTER", "key": "requests", "value": 1},
      {"type": "TIMER", "key": "resptime", "value": 20.2},
    ]
  
