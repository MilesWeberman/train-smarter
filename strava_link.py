import requests
from datasets import load_dataset
import pandas as pd

# heartrate data
useful_cols = ['start_date_loacl','start_time','start_date_local',
               'type', 'distance', 'moving_time', 'elapsed_time', 
                'average_speed', 'max_speed',
                'total_elevation_gain', 'elev_high', 'elev_low', 
                'average_cadence', 
                'has_heartrate', 'average_heartrate', 'max_heartrate', 
                'gear_id']

# no heartrate data
less_useful_cols = ['start_date_loacl','start_time','start_date_local',
                    'type', 'distance', 'moving_time', 'elapsed_time', 
                    'average_speed', 'max_speed',
                    'total_elevation_gain', 'elev_high', 'elev_low', 
                    'gear_id']

def get_user_data(refresh_token = 'd49a90f5fd6a887876ee79d83a3d525fdf82a4aa'):
    auth_url = "https://www.strava.com/oauth/token"
    activites_url = "https://www.strava.com/api/v3/athlete/activities"

    payload = {
        'client_id': "144773",
        'client_secret': 'deed6f325a821cba47f41427d03f01e82d2e89f9',
        'refresh_token': refresh_token,
        'grant_type': "refresh_token",
        'f': 'json'
    }

    # request token from api
    res = requests.post(auth_url, data=payload, verify=False)
    access_token = res.json()['access_token']

    # get dataset from api
    header = {'Authorization': 'Bearer ' + access_token}
    dfs = []

    for page in range(5):
        # use a max of 1,000 activities
        param = {'per_page': 200, 'page': page+1}
        my_dataset = requests.get(activites_url, headers=header, params=param).json()
        if len(my_dataset) == 0:
            # if nothing provided, dont save. should only be called if the number of activities is exactly a multiple of 200
            break

        activities = pd.json_normalize(my_dataset)

        # extract useful cols
        try:
            activities = activities[useful_cols]
        except KeyError:
            activities = activities[less_useful_cols]
        dfs.append(activities)

    df = pd.concat(dfs, ignore_index = True)
    df['start_date_local'] = pd.to_datetime(df['start_date_local'], format='%Y-%m-%dT%H:%M:%SZ', utc=True)
    df['start_time'] = df['start_date_local'].dt.time
    df['start_date_local'] = df['start_date_local'].dt.date

    df_run = df[df['type'].str.contains('Run')]
    df_cross = df[~df['type'].str.contains('Run')]

    return df_run, df_cross



def get_example_data():
    # download sample dat 
    ds = load_dataset("reach-vb/strava-stats")

    # convert to pandas
    ds.set_format(type="pandas")
    df = ds['train'][:]

    # extract useful columns
    df = df[useful_cols]
    df['start_date_local'] = pd.to_datetime(df['start_date_local'], format='%Y-%m-%dT%H:%M:%SZ', utc=True)
    df['start_time'] = df['start_date_local'].dt.time
    df['start_date_local'] = df['start_date_local'].dt.date

    # split runs and cross training
    df_run = df[df['type'].str.contains('Run')]
    df_cross = df[~df['type'].str.contains('Run')]

    return df_run, df_cross


def save_data(datatype = 'user', 
              refresh_token = 'd49a90f5fd6a887876ee79d83a3d525fdf82a4aa'):
    if datatype == 'example':
        df_run, df_cross = get_example_data()
    if datatype == 'user':
        df_run, df_cross = get_user_data(refresh_token)

    # save outputs to csv
    df_run.to_csv('data/run_data.csv')
    df_cross.to_csv('data/cross_data.csv')

if __name__ == 'main':
    try:
        save_data(datatype='user')
    except:
        save_data(datatype='example')