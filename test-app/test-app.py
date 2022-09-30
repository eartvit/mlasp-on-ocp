import os
import random
from wtforms import SubmitField, StringField
from flask_wtf import FlaskForm
import numpy as np
from flask import Flask, request, jsonify, session, url_for, render_template, redirect
import requests
import logging


def generateInputSequence(featSpace, exceptionList=None):
    """ 
    Iterates through the feature space dictionary and randomly selects a viable value to be added to the test feature
     object for each key in the dictionary.
    In case the key is found in the exceptionList, then it will randomly select  a value from the existing list,
     otherwise it will randomly select an element from the range applicable to the key.
    E.g.: featSpace = { key1:[min, max], key2:[value1, value2, value3]}, exceptionList=['key2'], then result will be a
     vector [random.randint(min, max), random.choice(value1, value2, value3)]
    Helper function used inside generateParameterCombinations function.
    
    Parameters:
        featSpace (dict): A dictionary defining the space of features of the model. The keys are the feature names and
         the values are applicable for the features. For a range, the values must be integers.
         For a choice, can be interger or float.
        exceptionList (list): The array of the feature names that should be used with random.choice(),
         i.e. multiple exact options possible instead of range.
        
    Returns:
        result(array): A feature vector, ordered as expected by the model.
    """
    if exceptionList is None:
        exceptionList = []
    result = []
    keys = list(featSpace)
    keys_len = len(featSpace.keys())
    for i in range(keys_len):
        val = 0
        if keys[i] in exceptionList:
            val = random.choice(featSpace.get(keys[i]))
        else:
            val = random.randint(featSpace[keys[i]][0], featSpace[keys[i]][1])

        result.append(val)

    return result

def generatePrediction(params):
    """
    Generate a prediction using the remote service endpoint. Uses a globally defined target service endpoint (loaded from the OS environment)
    Parameters:
        params(list): Ordered list (as expected by the model) of the test feature values.

    Returns:
        y_pred(array[float]): One dimensional array with the actual prediction (as float value).
    """
    ex = None
    results_OK = True
    resp = None
    y_pred = -1

    message = {
                "data": {
                    "ndarray": [params]
                }
              }

    try:
        resp = requests.post(url=ml_service_endpoint, json=message, verify=False)
        logging.info(f"Processed request results: {resp}")
    except Exception as e:
        results_OK = False
        ex = e
        logging.error(f"Prediction service exception: {ex}")

    if results_OK:
        y_pred = resp.json()['data']['ndarray'][0]
        print(f'Got prediction value {y_pred}')

    return y_pred


def generateParameterCombinations(featureSpace, exceptionList, epochs, precision, searchTarget):
    """
    Searches for valid parameter combinations for a model within a given feature space, using a desired precision from
    the target prediction. The search is executed for a number of epochs.
    This is the entry level function that gets a full dictionary of possible parameter options that yield the search
    target (throughput).
    
    Parameters:
        featureSpace(dict): A dictionary defining the space of features of the model. The keys are the feature names and
         the values are applicable for the features. For a range, the values must be integers.
         For a choice, can be interger or float.
            E.g. featSpace = { key1:[min, max], key2:[value1, value2, value3]}, exceptionList=['key2'],
             then result will be a vector [random.randint(min, max), random.choice(value1, value2, value3)
        exceptionList (list): The array of the feature names that should be used with random.choice(),
         i.e. multiple exact options possible instead of range.
        epochs(int): The number of iterations to use random search for potential parameter combinations.
        precision(float): The precision (absolute deviation percentage) of the predicted target from the search target.
        searchTarget(int): The desired prediction value of the model for which a set of features are searched.
         It can also be a floating point number.
        
    Returns:
        parameters(dict): A dictionary containing lists of values for eligible parameters falling within the search
         patterns, their associated predictions and deviation measurements.
         The dictionaly keys are 'parameters', 'deviation' and 'predictions'
            E.g.: {'parameters': [[val_11, val_21, val_31, val_41, , val_n1],
                                  [val_12, val_22, val_32, val_42, , val_n2]],
                   'deviation': [array([[dev1]]),
                                  array([[dev2]])],
                   'predictions': [array([[pred1]], dtype=float32),
                                  array([[pred2]], dtype=float32)]}
    """
    numParams = len(featureSpace.keys())
    zeros = np.zeros(numParams)  # temp for initialization
    parameters = [zeros]
    deviation = [0]
    predictions = [0]

    print(f'Generating {epochs} sequences...\n')

    for i in range(epochs):
        inputSequence = generateInputSequence(featureSpace, exceptionList)
        #y_pred = generatePrediction(inputSequence, model, trainingScaler, targetScaler)
        y_pred = generatePrediction(inputSequence)
        crt_dev = 100 * (abs(y_pred - searchTarget) / searchTarget)
        if crt_dev < precision:
            deviation.append(crt_dev)
            parameters.append(inputSequence)
            predictions.append(y_pred)

    parameters = parameters[1:]  # remove the first dummy element from all lists before creating the final output
    deviation = deviation[1:]
    predictions = predictions[1:]
    results = {'parameters': parameters, 'deviation': deviation, 'predictions': predictions}
    print(f'Done... Results are: {results} \n')
    return results


def extractBestParameterCombination(parameterCombinations):
    """
    Extracts the feature set from the input parameterCombinations dictionary created by the 'generateParameterCombinations'
     function closest to the search target (smallest deviation).
    
    Parameters:
        parameterCombinations(dict): A dictionary containing lists of values for eligible parameters falling within the
         search patterns, their associated predictions and deviation measurements. The dictionaly keys are 'parameters',
         'deviation' and 'predictions'
            E.g.: {'parameters': [[val_11, val_21, val_31, val_41, , val_n1],
                                  [val_12, val_22, val_32, val_42, , val_n2]],
                   'deviation': [array([[dev1]]),
                                  array([[dev2]])],
                   'predictions': [array([[pred1]], dtype=float32,
                                  array([[pred2]], dtype=float32}
        
    Returns:
        result(tuple): A three element tuple returning the parameters (a.k.a input features) array, the deviation percentage
         value from the searched target (as a float) and the predicted value for the given input set (as a float value).
    """

    parameters = parameterCombinations.get("parameters")
    deviation = parameterCombinations.get("deviation")
    predictions = parameterCombinations.get("predictions")
    
    pos = np.argmax(predictions)
    paramMap = {'asyncResp': parameters[pos][0], 'asyncRespThreads': parameters[pos][1],
                'cThreads': parameters[pos][2], 'jacptQSize': parameters[pos][3],
                'jacptThreads': parameters[pos][4], 'ltTargetSize': parameters[pos][5],
                'numConnections': parameters[pos][6], 'timeoutSeconds': parameters[pos][7]
                }
    bestCombination = {'Parameters': paramMap,
                       'Deviation': deviation[pos],
                       'Prediction': float(predictions[pos])}
    return bestCombination


def num(s):
    try:
        return int(s)
    except ValueError:
        return float(s)


def extractFeatureSpace(content):    
    features = {'asyncResp': list(map(bool, content['asyncResp'].split(','))),
                'asyncRespThreads': list(map(num, content['asyncRespThreads'].split(','))),
                'cThreads': list(map(num, content['cThreads'].split(','))),
                'jacptQSize': list(map(num, content['jacptQSize'].split(','))),
                'jacptThreads': list(map(num, content['jacptThreads'].split(','))),
                'ltTargetSize': list(map(num, content['ltTargetSize'].split(','))),
                'numConnections': list(map(num, content['numConnections'].split(','))),
                'timeoutSeconds': list(map(num, content['timeoutSeconds'].split(',')))}
    print(f'Features are: {features}\n')
    return features


def extractExceptionList(features):
    exceptionList = []
    keys = list(features)
    keys_len = len(features.keys())
    for i in range(keys_len):
        # print(f'Key:{keys[i]}, feature:{features[keys[i]]}, length:{len(features[keys[i]])}')
        if len(features[keys[i]]) > 2:
            exceptionList.append(keys[i])
    print(f'Exception list is: {exceptionList}\n')
    return exceptionList


def extractEpochs(content):
    epochsValue = content['Epochs']
    epochs = num(epochsValue)
    return epochs


def extractPrecision(content):
    precisionValue = content['Precision']
    precision = num(precisionValue)
    return precision


def extractSearchTarget(content):
    searchTargetValue = content['SearchTargetValue']
    searchTarget = num(searchTargetValue)
    return searchTarget


app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey'

class MLASPConfigForm(FlaskForm):    
    asyncResp = StringField('asyncResp')
    asyncRespThreads = StringField('asyncRespThreads')
    cThreads = StringField('cThreads')
    jacptQSize = StringField('jacptQSize')
    jacptThreads = StringField('jacptThreads')
    ltTargetSize = StringField('ltTargetSize')
    numConnections = StringField('numConnections')
    timeoutSeconds = StringField('timeoutSeconds')

    Epochs = StringField('Epochs')
    Precision = StringField('Precision')
    SearchTargetValue = StringField('SearchTargetValue')
    submit = SubmitField('Submit')


@app.route("/", methods=["GET", "POST"])
def index():
    # return '<h1> Flask is running</h1>'
    form = MLASPConfigForm()
    
    if form.validate_on_submit():
        session['asyncResp'] = form.asyncResp.data
        session['asyncRespThreads'] = form.asyncRespThreads.data
        session['cThreads'] = form.cThreads.data
        session['jacptQSize'] = form.jacptQSize.data
        session['jacptThreads'] = form.jacptThreads.data
        session['ltTargetSize'] = form.ltTargetSize.data
        session['numConnections'] = form.numConnections.data
        session['timeoutSeconds'] = form.timeoutSeconds.data
        
        session['Epochs'] = form.Epochs.data
        session['Precision'] = form.Precision.data
        session['SearchTargetValue'] = form.SearchTargetValue.data
        return redirect(url_for("prediction"))
    return render_template('home.html', form=form)


@app.route("/prediction")
def prediction():
    results = "No valid combination found for given limits and search target value and precision"
    featureSpace = extractFeatureSpace(session)
    exceptionList = extractExceptionList(featureSpace)
    epochs = extractEpochs(session)
    precision = extractPrecision(session)
    searchTarget = extractSearchTarget(session)

    parameterCombinations = generateParameterCombinations(featureSpace, exceptionList, epochs, precision, searchTarget)
    if len(parameterCombinations.get("parameters")) == 0:
        print(f'No valid combination found for given limits and search target value and precision\n')
        # return "No valid combination found for given limits and search target value and precision"
    else:
        bestParamCombination = extractBestParameterCombination(parameterCombinations)
        print(f'Best parameter combination:{bestParamCombination}')
        # results = jsonify(bestParamCombination)
        results = bestParamCombination

    return render_template('prediction.html', results=results)


@app.route("/api/predict", methods=["POST"])
def ml_predict():
    content = request.json
    featureSpace = extractFeatureSpace(content)
    exceptionList = extractExceptionList(featureSpace)
    epochs = extractEpochs(content)
    precision = extractPrecision(content)
    searchTarget = extractSearchTarget(content)

    parameterCombinations = generateParameterCombinations(featureSpace, exceptionList, epochs, precision, searchTarget)
    if len(parameterCombinations.get("parameters")) == 0:
        print(f'No valid combination found for given limits and search target value and precision\n')
        return "No valid combination found for given limits and search target value and precision"
    else:
        bestParamCombination = extractBestParameterCombination(parameterCombinations)
        print(f'Best parameter combination:{bestParamCombination}')
        return jsonify(bestParamCombination)


service_port = os.environ['SERVICE_PORT']
ml_service_endpoint = os.environ['ML_SERVICE_ENDPOINT']

if __name__ == '__main__':
    app.run(host="0.0.0.0", port=service_port)