import streamlit as st
import json
import datetime
import pandas as pd
import io
import openai
import datetime

def load_training_plans():
    try:
        with open("training_plans.json", "r") as file:
            return json.load(file)
    except FileNotFoundError:
        st.error("The training plans file was not found.")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

def get_training_plan(level, days_per_week):
    data = load_training_plans()
    if data is None:
        return None
    
    for plan in data["plans"]:
        if plan["level"] == level and plan["days_per_week"] == days_per_week:
            return plan["schedule"]
    return None

def get_starting_monday():
    today = datetime.date.today()
    days_until_monday = (7 - today.weekday()) % 7
    return today + datetime.timedelta(days=days_until_monday)

def get_data(exercise_type = 'run'):
    return pd.read_csv(f'data/{exercise_type}_data.csv')


def main():
    st.title("🏃 Train Smartest")
    
    # Initialize session states
    if "signed_up" not in st.session_state:
        st.session_state.signed_up = False
        st.session_state.user_data = {}
        st.session_state.notes = ""
    
    # If user hasn't signed up, show form
    if not st.session_state.signed_up:
        st.subheader("Sign Up for Your Personalized Training Plan")
        
        name = st.text_input("Enter your name")
        birthday = st.date_input(
            "Birthday",
            min_value=datetime.date.today() - datetime.timedelta(days=365*99),
            max_value=datetime.date.today() - datetime.timedelta(days=365*18)
        )
        gender = st.selectbox("Gender", ["Male", "Female", "Other", "Prefer not to say"])
        fitness_level = st.selectbox("Overall Fitness Level", ["Beginner", "Intermediate", "Advanced"])
        weekly_mileage = st.number_input("Current Weekly Mileage (km)", min_value=0, step=1)
        long_run = st.number_input("Longest Run in the Past Month (km)", min_value=0, step=1)
        training_days = st.slider("How many days per week can you run?", 3, 6, 4)
        race_date = st.date_input("Marathon Race Date", min_value=datetime.date.today())
        
        col1, col2 = st.columns(2)
        with col1:
            target_hours = st.number_input(
                "Target Marathon Time (Hours)", 
                min_value=2, 
                max_value=7, 
                step=1, 
                key="target_hours", 
                format="%d"
            )
        with col2:
            target_minutes = st.number_input(
                "Target Marathon Time (Minutes)", 
                min_value=0, 
                max_value=59, 
                step=1, 
                key="target_minutes", 
                format="%02d"
            )
        target_time = datetime.time(hour=target_hours, minute=target_minutes)

        non_running_exercise = st.radio("Do you plan on doing any non-running exercise?", ["No", "Yes"])
        if non_running_exercise == "Yes":
            non_running_days = st.slider("How many days per week?", 1, 7, 2)
        else:
            non_running_days = 0

        past_injury = st.radio("Have you ever had a running-related injury?", ["No", "Yes"])

        injury_type, injury_recovery = None, None
        if past_injury == "Yes":
            injury_type = st.selectbox(
                "What type of injury?",
                [
                    "Shin Splints", 
                    "Stress Fracture", 
                    "Runner’s Knee", 
                    "IT Band Syndrome",
                    "Achilles Tendinitis", 
                    "Plantar Fasciitis", 
                    "Muscle Strain", 
                    "Other"
                ]
            )
            injury_recovery = st.radio("Have you fully recovered?", ["Yes", "No"])
        
        current_pain = st.radio("Are you currently experiencing any pain or discomfort?", ["No", "Yes"])

        pain_location, pain_severity = None, None
        if current_pain == "Yes":
            pain_location = st.selectbox(
                "Where is the pain?",
                ["Foot", "Ankle", "Knee", "Hip", "Lower Back", "Other"]
            )
            pain_severity = st.slider("Pain severity (1 = mild, 10 = severe)", 1, 10, 3)

        # When user clicks Generate
        if st.button("Generate Training Plan"):
            # Basic feasibility check for beginners
            if (
                fitness_level == "Beginner" 
                and weekly_mileage == 0 
                and long_run == 0 
                and (race_date - datetime.date.today()).days < 70
            ):
                st.error("We recommend a longer training period for running the race. Please adjust your race date or training parameters before continuing.")
                return
            
            # Store user data
            st.session_state.user_data = {
                "name": name,
                "birthday": str(birthday),
                "gender": gender,
                "fitness_level": fitness_level.lower(),
                "weekly_mileage": weekly_mileage,
                "long_run": long_run,
                "training_days": training_days,
                "race_date": str(race_date),
                "target_time": str(target_time),
                "past_injury": past_injury,
                "injury_type": injury_type,
                "injury_recovery": injury_recovery,
                "current_pain": current_pain,
                "pain_location": pain_location,
                "pain_severity": pain_severity,
            }

            # OpenAI Integration
            openai.api_key = st.secrets["OPENAI_API_KEY"]
            
            # 1) Check if feasible
            messages = [
                {
                    "role": "system",
                    "content": (
                        "You are a highly skilled running coach. "
                        "Given the user's data, determine if this is feasible for them to run a marathon "
                        "given their target date and target time. "
                        "Only respond with either 'feasible' or 'not feasible' and no other text. "
                        "Consider the user's fitness level, weekly mileage, long run, race date, injuries, and target time."
                        "Don't be too conservative allowing optimism for comletion time if reasonable."
                    )
                },
                {
                    "role": "user",
                    "content": f"User data: {st.session_state.user_data}"
                }
            ]

            try:
                response = openai.ChatCompletion.create(
                    model="gpt-4o",  # or "gpt-3.5-turbo", etc. 
                    messages=messages,
                    temperature=0.3,
                    max_tokens=100
                )
                feasibility = response.choices[0].message["content"].strip()
            except Exception as e:
                st.error(f"OpenAI API Error: {e}")
                return
      
            # 2) If feasible, proceed. Otherwise, get reason, show error, and reset.
            if "feasible" == feasibility.lower():
                st.session_state.signed_up = True
                st.rerun()
            else:
                # Get a short reason
                try:
                    reason_messages = [
                        {
                            "role": "system",
                            "content": (
                                "You are a highly skilled running coach. "
                                "The user was deemed 'not feasible' to run the marathon. "
                                "Provide a concise, one-sentence reason why. In correct english"
                            )
                        },
                        {
                            "role": "user",
                            "content": f"User data: {st.session_state.user_data}"
                        }
                    ]
                    reason_response = openai.ChatCompletion.create(
                        model="gpt-4o",
                        messages=reason_messages,
                        temperature=0.5,
                        max_tokens=100
                    )
                    reason_text = reason_response.choices[0].message["content"].strip()
                except Exception as e:
                    reason_text = "An unknown reason. (OpenAI API Error)"

                st.error(
                    f"**Marathon Not Feasible.**\n\n"
                    f"**Reason:** {reason_text}\n\n"
                    "Please adjust your parameters before continuing."
                )
                

                # Clear old data, revert to sign-up mode, and rerun
                st.session_state.user_data = {}
                # st.session_state.signed_up = False
                # st.rerun()
                return

    # If user is signed up, show the training plan
    else:
        st.subheader(f"Welcome, {st.session_state.user_data['name']}!")
        st.write("Here is your personalized training plan.")
        st.subheader("🏁 Your Marathon Goal")
        st.write(f"**Race Date:** {st.session_state.user_data['race_date']}")
        st.write(f"**Target Time:** {st.session_state.user_data['target_time']}")

        user_fitness_level = st.session_state.user_data["fitness_level"]
        user_days = st.session_state.user_data["training_days"]

        training_plan = get_training_plan(user_fitness_level, user_days)

        if st.session_state.user_data['weekly_mileage'] > 0:
            user_weekly_mileage = st.session_state.user_data['weekly_mileage']
            for week in training_plan:
                if week['total_distance_km'] > user_weekly_mileage:
                    for i in range(week['week'] - 1):
                        training_plan[i]['runs'] = week['runs']
                        training_plan[i]['total_distance_km'] = week['total_distance_km']
                    break



        if training_plan:
            start_date = get_starting_monday()
            
            st.subheader("This Week's Plan")
            today = datetime.date.today()
            selected_week_data = next(
                (
                    week for week in training_plan 
                    if start_date + datetime.timedelta(weeks=week['week'] - 1) <= today <=
                       start_date + datetime.timedelta(weeks=week['week'] - 1, days=6)
                ), 
                None
            )
            if not selected_week_data:
                selected_week_data = next(
                    (
                        week for week in training_plan 
                        if start_date + datetime.timedelta(weeks=week['week'] - 1) > today
                    ),
                    None
                )

            if selected_week_data:
                st.write(
                    f"**Week {selected_week_data['week']} Note:** "
                    f"{selected_week_data.get('note', 'No notes for this week.')}"
                )
                st.write(f"**Total Distance:** {selected_week_data.get('total_distance_km', 'N/A')} km")
            
            current_week_runs = []
            upcoming_week_runs = []
            for week in training_plan:
                week_start = start_date + datetime.timedelta(weeks=week['week'] - 1)
                week_end = week_start + datetime.timedelta(days=6)
                
                if week_start <= today <= week_end:
                    current_week_runs = week['runs']
                    break
                elif today < week_start and not upcoming_week_runs:
                    upcoming_week_runs = week['runs']

            display_runs = current_week_runs if current_week_runs else upcoming_week_runs
            if display_runs:
                df_current_week = pd.DataFrame(display_runs)
                df_current_week.insert(
                    1, 'Date', [
                        (
                            start_date + datetime.timedelta(
                                weeks=0,  # Always start from week 1
                                days=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].index(run['day'])
                            )
                        ).strftime('%d/%m/%Y')
                        for run in display_runs
                    ]
                )
                st.table(df_current_week)
            else:
                st.write("No runs scheduled for this week.")
            
            # get most recent runs
            df_run = get_data(exercise_type = 'run')
            df_run = df_run[['start_date_local', 'distance', 'elapsed_time']]
            df_run.rename(columns = {'start_date_local':'Date', 'distance':'Distance (km)','elapsed_time': 'Time'},
                        inplace = True)
            df_run['Distance (km)'] = df_run['Distance (km)']/1000
            df_run['Distance (km)'] = df_run['Distance (km)'].round(2)
            df_run['Time'] = df_run['Time'].apply(lambda x :str(datetime.timedelta(seconds = x)))

            # select only the 5 most recent runs
            df_run = df_run.sort_values(by = 'Date', ascending = False)[:5]

            # display
            st.write('**Your most recent runs:** (from Strava)')
            st.table(df_run.style.format({"Distance (km)": "{:.2f}".format}))

            with st.expander("View Selected Week"):
                selected_week = st.selectbox(
                    "Select a week to view",
                    [week['week'] for week in training_plan],
                    key='selected_week'
                )
                df_full_plan = pd.DataFrame([
                    {
                        **run,
                        'Week': week['week'],
                        'Date': (
                            start_date + datetime.timedelta(
                                weeks=week['week'] - 1,
                                days=['Monday','Tuesday','Wednesday','Thursday','Friday','Saturday','Sunday'].index(run['day'])
                            )
                        ).strftime('%d/%m/%Y')
                    }
                    for week in training_plan
                    for run in week['runs']
                    if week['week'] == selected_week
                ])
                df_full_plan = df_full_plan[['Week', 'Date'] + [col for col in df_full_plan.columns if col not in ['Week', 'Date']]]
                st.table(df_full_plan)
                
                # Excel download
                full_df = pd.DataFrame(training_plan)
                output = io.BytesIO()
                full_df.drop(columns=['injury_risk'], inplace=True, errors='ignore')
                df_pivot = pd.DataFrame(columns=['Week', 'Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday', 'Sunday'])
                
                for week in training_plan:
                    week_data = {'Week': week['week']}
                    for run in week['runs']:
                        week_data[run['day']] = f"{run['type']} ({run['distance_km']}km)"
                    df_pivot = pd.concat([df_pivot, pd.DataFrame([week_data])], ignore_index=True)

                df_pivot.to_excel(output, index=False, engine='openpyxl')
                output.seek(0)
                st.download_button("Download Training Plan as Excel", output, "training_plan.xlsx")


        else:
            st.error("No matching training plan found. Try adjusting your inputs.")
        
        

        if st.button("Reset"):
            st.session_state.signed_up = False
            st.session_state.user_data = {}
            st.session_state.notes = ""
            st.rerun()

if __name__ == "__main__":
    main()
