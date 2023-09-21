# File: stock_prediction.py
# Authors: Cheong Koo and Bao Vo
# Date: 14/07/2021(v1); 19/07/2021 (v2); 25/07/2023 (v3)

# Further iterations by Naca Hitchman

# Code modified from:
# Title: Predicting Stock Prices with Python
# Youtuble link: https://www.youtube.com/watch?v=PuZY9q-aKLw
# By: NeuralNine

# Need to install the following:
# pip install numpy
# pip install matplotlib
# pip install pandas
# pip install tensorflow
# pip install scikit-learn
# pip install pandas-datareader
# pip install yfinance

from msilib import Feature
import numpy as np
import matplotlib.pyplot as plt
import mplfinance as mpf
import matplotlib.dates as mdates
import pandas as pd
import pandas_datareader as web
import datetime as dt
import tensorflow as tf
import yfinance as yf
import os
import pickle
import csv
from sklearn import preprocessing
from sklearn.preprocessing import MinMaxScaler
from sklearn.model_selection import train_test_split
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import LSTM, GRU, SimpleRNN, Bidirectional, Dropout, Dense, ConvLSTM2D
from keras.layers import Reshape


import matplotlib.pyplot as plt

#task 5
#   multi step prediction function
def create_sequences_ms(data, seq_length, n_steps_ahead):
    xs = []
    ys = []
    for i in range(len(data)-(seq_length+n_steps_ahead)+1):
        x = data[i:(i+seq_length)]
        y = data[(i+seq_length):(i+seq_length+n_steps_ahead)]
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)

def create_sequences_mv(data, seq_length):
    xs = []
    ys = []
    for i in range(len(data)-(seq_length+1)):
        x = data[i:(i+seq_length)]
        y = data[i+seq_length]
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)

def create_sequences(data, seq_length, n_steps_ahead):
    xs = []
    ys = []
    for i in range(len(data)-(seq_length+n_steps_ahead)+1):
        x = data[i:(i+seq_length)]
        y = data[i+seq_length:i+seq_length+n_steps_ahead]  # keep all features for the next n_steps_ahead days
        xs.append(x)
        ys.append(y)
    return np.array(xs), np.array(ys)

#task 4
def create_model(sequence_length, n_features, n_steps_ahead, units=[256], cells=['LSTM'], n_layers=2, dropout=0.3,
                loss="mean_absolute_error", optimizer="rmsprop", bidirectional=False):
    model = Sequential()
    for i in range(n_layers):
        cell_name = cells[i]
        if cell_name not in globals():
            raise ValueError(f"Invalid layer network type: {cell_name}")
        cell = globals()[cell_name]
        unit = units[i]
        if i == 0:
            if bidirectional:
                model.add(Bidirectional(cell(unit, return_sequences=True), batch_input_shape=(None, sequence_length, n_features)))
            else:
                model.add(cell(unit, return_sequences=True, batch_input_shape=(None, sequence_length, n_features)))
        elif i == n_layers - 1:
            if bidirectional:
                model.add(Bidirectional(cell(unit, return_sequences=False)))
            else:
                model.add(cell(unit, return_sequences=False))
        else:
            if bidirectional:
                model.add(Bidirectional(cell(unit, return_sequences=True)))
            else:
                model.add(cell(unit, return_sequences=True))
        model.add(Dropout(dropout))
    model.add(Dense(n_steps_ahead * n_features, activation="linear"))  # Adjusted for multi-step, multivariate prediction
    model.add(Reshape((n_steps_ahead, n_features)))  # Reshape the output to have shape (n_steps_ahead, n_features)
    model.compile(loss=loss, metrics=[loss], optimizer=optimizer)
    return model

#task 3
def plot_boxplot(df, n, columns):
    # Calculate the rolling window data for each column
    rolling_data = [df[column].rolling(n).mean() for column in columns]
    
    # Create the box plot
    fig, ax = plt.subplots()
    ax.boxplot([data.dropna() for data in rolling_data], labels=columns)
    ax.set_title(f'{n} Day Rolling Window')
    
    # Show the plot
    plt.show()

#task 3
def plot_candlestick(df, n=1):
    # Resample the data to have one row per n trading days
    df = df.resample(f'{n}D').agg({'Open': 'first', 'High': 'max', 'Low': 'min', 'Close': 'last'})
    # Create the candlestick chart
    mpf.plot(df, type='candle')

#task 2
def downloadData(ticker, start_date, end_date, save_file=False):
     #create data folder in working directory if it doesnt already exist
    data_dir = os.path.join(os.getcwd(), 'data')
    if not os.path.exists(data_dir):
        os.makedirs(data_dir)
    data = None 
    #if ticker is a string, load it from yfinance library
    if isinstance(ticker, str):
        # Check if data file exists based on ticker, start_date and end_date
        file_path = os.path.join(data_dir, f"{ticker}_{start_date}_{end_date}.csv")
        if os.path.exists(file_path):
            # Load data from file
            data = pd.read_csv(file_path)
        else:
            # Download data using yfinance
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            # Save data to file if boolean save_file is True
            if save_file:
                data.to_csv(file_path) 
    #if passed in ticker is a dataframe, use it directly
    elif isinstance(ticker, pd.DataFrame):
        # already loaded, use it directly
        data = ticker
    else:
        # raise error if ticker is neither a string nor a dataframe
        raise TypeError("ticker can be either a str or a `pd.DataFrame` instances")

    # return the dataframe
    return data

def processNANs(df, fillna_method):
    # Deal with potential NaN values in the data
    # Drop NaN values
    if fillna_method == 'drop':
        df.dropna(inplace=True)
    #use forward fill method, fill NaN values with the previous value
    elif fillna_method == 'ffill':
        df.fillna(method='ffill', inplace=True)
    #use backward fill method, fill NaN values with the next value
    elif fillna_method == 'bfill':
        df.fillna(method='bfill', inplace=True)
    #use mean method, fill NaN values with the mean of the column
    elif fillna_method == 'mean':
        df.fillna(data.mean(), inplace=True)

    return df
#task 2 - function to load and process a dataset with multiple features
def processData(
    ticker, 
    start_date, 
    end_date, 
    save_file, 
    prediction_column, 
    prediction_days, 
    feature_columns=[], 
    split_method='date', 
    split_ratio=0.8, 
    split_date=None, 
    fillna_method='drop', 
    scale_features=False, 
    scale_min=0, 
    scale_max=1,
    save_scalers=False,
    n_steps=5,  # number of future days to predict
    task5method=0):  # whether to use multiple features
    
    data = downloadData(ticker, start_date, end_date, save_file)
   
    # this will contain all the elements we want to return from this function
    result = {}
    # we will also return the original dataframe itself
    result['df'] = data.copy()
   
    # make sure that the passed feature_columns exist in the dataframe
    if len(feature_columns) > 0:
        for col in feature_columns:
            assert col in data.columns, f"'{col}' does not exist in the dataframe."
    else:
        # if no feature_columns are passed, use all columns except the prediction_column
        feature_columns = list(filter(lambda column: column != 'Date', data.columns))
    
    # add feature columns to result
    result['feature_columns'] = feature_columns
    # Deal with potential NaN values in the data
    # Drop NaN values
    data = processNANs(data, fillna_method)

    # Split data into train and test sets based on date
    if split_method == 'date':
        train_data = data.loc[data['Date'] < split_date]
        test_data = data.loc[data['Date'] >= split_date]
    # Split data into train and test sets randomly with provided ratio
    elif split_method == 'random':
        train_data, test_data = train_test_split(data, train_size=split_ratio, random_state=42)
    
    # Reset index of both dataframes
    train_data = train_data.reset_index()
    test_data = test_data.reset_index()
    # Sort dataframes by date
    train_data = train_data.sort_values(by='Date')
    test_data = test_data.sort_values(by='Date')

    # Scale features
    if scale_features:
        # Create scaler dictionary to store all scalers for each feature column
        scaler_dict = {}
        # Dictionaries to store scaled train and test data
        scaled_train_data = {}
        scaled_test_data = {}
        #loop through each feature column
        for col in feature_columns:
            # Create scaler for each feature column using Min Max, passing in the scale_min and scale_max
            scaler = MinMaxScaler(feature_range=(scale_min, scale_max))
            # Fit and transform scaler on train data
            scaled_train_data[col] = scaler.fit_transform(train_data[col].values.reshape(-1, 1)).ravel()
            # Transform test data using scaler
            scaled_test_data[col] = scaler.transform(test_data[col].values.reshape(-1,1)).ravel()
            # Add scaler to scaler dictionary, using the feature column name as key
            scaler_dict[col] = scaler
        # Add scaler dictionary to result
        result["column_scaler"] = scaler_dict
        
         # Save scalers to file
        if save_scalers:
            # Create scalers directory if it doesn't exist
            scalers_dir = os.path.join(os.getcwd(), 'scalers')
            if not os.path.exists(scalers_dir):
                os.makedirs(scalers_dir)
            # Create scaler file name
            scaler_file_name = f"{ticker}_{start_date}_{end_date}_scalers.txt"
            scaler_file_path = os.path.join(scalers_dir, scaler_file_name)
            with open(scaler_file_path, 'wb') as f:
                pickle.dump(scaler_dict, f)
       
        # Convert scaled data to dataframes
        train_data = pd.DataFrame(scaled_train_data)
        test_data = pd.DataFrame(scaled_test_data)

    # Add train and test data to result
    result["scaled_train"] = train_data
    result["scaled_test"] = test_data
    # Construct the X's and y's for the training data
    result["scaled_train"] = train_data
    result["scaled_test"] = test_data
    X_train, y_train = create_sequences(train_data[feature_columns].values, prediction_days, n_steps)
    print(y_train.shape)
    print(X_train.shape)
    result["X_train"] = X_train
    result["y_train"] = y_train
    #result["X_train"] = np.reshape(result["X_train"], (result["X_train"].shape[0], result['X_train'].shape[1], -1));
    X_test, y_test = create_sequences(test_data[feature_columns].values, prediction_days, n_steps) 
    print(y_test.shape)
    print(X_test.shape)
    #X_test = np.array(X_test)
    #y_test = np.array(y_test)
    result["y_test"] = y_test
    result["X_test"] = X_test
    #result["X_test"] = np.reshape(X_test, (X_test.shape[0], X_test.shape[1], len(feature_columns)));


    return result

#------------------------------------------------------------------------------
# Load and process data using Task B.2 Function
# ------------------------------------------------------------------------------

# define function parameters to use
DATA_SOURCE = "yahoo"
COMPANY = "TSLA"  
DATA_START_DATE = '2015-01-01'
DATA_END_DATE = '2022-12-31'
SAVE_FILE = True
PREDICTION_DAYS = 100
SPLIT_METHOD = 'random'
SPLIT_RATIO = 0.8
SPLIT_DATE = '2020-01-02'
NAN_METHOD = 'drop'
FEATURE_COLUMNS = ['Open', 'High', 'Low', 'Close', 'Adj Close', 'Volume']
SCALE_FEATURES = True
SCALE_MIN = 0
SCALE_MAX = 1
SAVE_SCALERS = True
prediction_column = "Close"
N_STEPS = 5;

# Call processData function passing in parameters
data = processData(
    ticker=COMPANY, 
    start_date=DATA_START_DATE, 
    end_date=DATA_END_DATE, 
    save_file=SAVE_FILE,
    prediction_column=prediction_column,
    prediction_days=PREDICTION_DAYS,
    split_method=SPLIT_METHOD, 
    split_ratio=SPLIT_RATIO, 
    split_date=SPLIT_DATE,
    fillna_method=NAN_METHOD,
    feature_columns=FEATURE_COLUMNS,
    scale_features=SCALE_FEATURES,
    scale_min=SCALE_MIN,
    scale_max=SCALE_MAX,
    save_scalers=SAVE_SCALERS,
    n_steps=N_STEPS
    )
#task 4 candlestick
#plot_candlestick(processNANs(downloadData(COMPANY, '2022-05-01', '2022-05-31', False), 'drop'), 5)

#plot_boxplot(processNANs(downloadData(COMPANY, '2019-01-01', '2022-12-31', False),'drop'),['Open', 'High', 'Low', 'Close', 'Adj Close'], 10)

#task 4 bloxplot
#plot_boxplot(downloadData(COMPANY, '2019-01-01', '2022-12-31', False), 40, ['Open', 'High', 'Low', 'Close', 'Adj Close'])
# Number of days to look back to base the prediction
#PREDICTION_DAYS = 60 # Original

#------------------------------------------------------------------------------
#Task 4
sequence_length = data['X_train'].shape[1]
n_features = data['X_train'].shape[2]
#set 1

units = [256, 256]
cells = ['LSTM', 'LSTM']
n_layers = 2
dropout = 0.3
loss = "mean_absolute_error"
optimizer = "rmsprop"
bidirectional = True

# Set the number of epochs and batch size
epochs = 30
batch_size = 32


#set 2
"""
# Set the model parameters
units = [256, 128, 64]
cells = ['LSTM', 'GRU', 'SimpleRNN']
n_layers = 3
dropout = 0.2
loss = "mean_squared_error"
optimizer = "adam"
bidirectional = True

# Set the training parameters
epochs = 25
batch_size = 32
"""
#set 3
"""
# Set the model parameters
units = [512, 256]
cells = ['GRU', 'GRU']
n_layers = 2
dropout = 0.4
loss = "mean_absolute_percentage_error"
optimizer = "sgd"
bidirectional = False

# Set the training parameters
epochs = 35
batch_size = 64
"""

#set 4
"""
# Set the model parameters
units = [128, 64, 32]
cells = ['SimpleRNN', 'SimpleRNN', 'SimpleRNN']
n_layers = 3
dropout = 0.5
loss = "huber_loss"
optimizer = "adagrad"
bidirectional = True

# Set the training parameters
epochs = 15
batch_size = 16
"""


# Create the model using the create_model function
model = create_model(sequence_length, n_features, units=units, cells=cells, n_layers=n_layers,
                     dropout=dropout, loss=loss, optimizer=optimizer, bidirectional=bidirectional, n_steps_ahead=N_STEPS)



# Train the model on the training data
model.fit(data['X_train'], data['y_train'], epochs=epochs, batch_size=batch_size)

closing_price_index = FEATURE_COLUMNS.index(prediction_column)

# Get the actual prices
actual_prices = data["column_scaler"][prediction_column].inverse_transform(data["y_test"][:, -1, closing_price_index].reshape(-1,1)).ravel()
# Predict the prices
predicted_prices = model.predict(data['X_test'])
predicted_close_prices = predicted_prices[:, -1, closing_price_index].reshape(-1, 1)
predicted_close_prices = data["column_scaler"][prediction_column].inverse_transform(predicted_close_prices).ravel()
# Plot the actual and predicted prices
plt.plot(actual_prices, color="black", label=f"Actual {COMPANY} Price")
plt.plot(predicted_close_prices, color="green", label=f"Predicted {COMPANY} Price")
plt.title(f"{COMPANY} Share Price")
plt.xlabel("Time")
plt.ylabel(f"{COMPANY} Share Price")
plt.legend()
plt.show()

# Save the predicted and actual prices to csv files
predicted_prices = predicted_close_prices.ravel()
actual_prices = actual_prices.ravel()
df = pd.DataFrame(predicted_close_prices)
df.to_csv('predicted_prices.csv', index=False)
df = pd.DataFrame(actual_prices)
df.to_csv('actual_prices.csv', index=False)

# Predict the next k days
real_data = [data['X_test'][-1, :, :]]
real_data = np.array(real_data)
print(real_data.shape)
real_data = np.reshape(real_data, (real_data.shape[0], real_data.shape[1], n_features))

# Predict the next k days
prediction = model.predict(real_data)  # shape: (1, k, n_features)
prediction = data["column_scaler"][prediction_column].inverse_transform(prediction[:, :, closing_price_index])  # shape: (1, k)

# Loop over the prediction and print each day's predicted price
for i, price in enumerate(prediction[0]):
    print(f"Prediction for day {i+1}: {price}")
