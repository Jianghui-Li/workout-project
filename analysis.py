import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
import altair as alt
import json
from openai import OpenAI

def get_ai_analysis(df):
    """
    Get AI analysis of workout history with time period consideration
    
    Args:
        df: pandas DataFrame containing workout data
    """
    try:
        client = OpenAI(api_key=st.secrets["API_KEY"])
        
        start_date = df['date'].min().strftime('%Y-%m-%d')
        end_date = df['date'].max().strftime('%Y-%m-%d')
        total_days = (df['date'].max() - df['date'].min()).days + 1
        total_workouts = len(df)
        days_active = df['date'].nunique()
        muscle_groups = df['muscle_group'].value_counts().to_dict()
        workout_types = df['workout_type'].value_counts().to_dict()
        difficulty_levels = df['difficulty'].value_counts().to_dict()
        
        prompt = f"""
        As a fitness expert, analyze the workout history from {start_date} to {end_date} ({total_days} days):
        - Total exercises performed: {total_workouts}
        - Active days: {days_active}
        - Muscle groups targeted (with frequency): {muscle_groups}
        - Types of workouts performed: {workout_types}
        - Difficulty levels: {difficulty_levels}

        Provide a brief analysis including:
        1. Overall consistency and commitment
        2. Balance of muscle groups (any imbalances?)
        3. Progression in difficulty over this time period
        4. Specific recommendations for improvement based on this time period
        Keep the analysis concise but specific to this user's data.
        Consider the time period when making your analysis - if it's a short period, focus on initial progress. 
        If it's longer, focus on trends and progression.
        """
        
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "You are a knowledgeable fitness instructor analyzing workout data. While output report, address the user as you/your."},
                {"role": "user", "content": prompt}
            ],
            temperature=0.1
        )
        
        analysis = response.choices[0].message.content
        period_context = f"\nAnalysis Period: {start_date} to {end_date} ({total_days} days)"
        
        return period_context + "\n\n" + analysis
        
    except Exception as e:
        return f"Unable to generate AI analysis: {str(e)}"

def load_workout_log(username):
    """Load and process workout log history"""
    log_file = f"file/workout_log_hist_{username}.json"
    try:
        with open(log_file, 'r') as f:
            memories = json.load(f)
            
        if not memories:
            st.warning("No workout data found. Start working out to see analysis!")
            return None
            
        df = pd.DataFrame(memories)
        df['date'] = pd.to_datetime(df['date'])
        return df
    except (FileNotFoundError, json.JSONDecodeError):
        st.warning("No workout data found. Start working out to see analysis!")
        return None

def create_activity_heatmap(df):
    """Create a heatmap of exercise activity"""
    if df is None or df.empty:
        return None

    daily_activity = df.groupby('date').size().reset_index()
    daily_activity.columns = ['date', 'exercises']

    chart = alt.Chart(daily_activity).mark_rect().encode(
        x=alt.X('date:T', title='Date', timeUnit='yearmonthdate'),  # Changed to temporal type with timeUnit
        color=alt.Color('exercises:Q', 
                       scale=alt.Scale(scheme='blues'),
                       legend=alt.Legend(title='Exercises')),
    ).properties(
        title='Exercise Activity Heatmap',
        width=600,
        height=100
    )
    
    return chart
def create_workout_type_chart(df):
    """Create a chart showing workout type distribution"""
    if df is None or df.empty:
        return None
        
    workout_counts = df['workout_type'].value_counts()
    
    chart = alt.Chart(workout_counts.reset_index()).mark_bar().encode(
        x=alt.X('workout_type:N', title='Workout Type'),
        y=alt.Y('count:Q', title='Number of Exercises'),
        color=alt.Color('workout_type:N', legend=None)
    ).properties(
        title='Workout Type Distribution'
    )
    
    return chart

def create_muscle_group_chart(df):
    """Create a chart showing muscle group distribution"""
    if df is None or df.empty:
        return None
        
    muscle_counts = df['muscle_group'].value_counts()
    
    chart = alt.Chart(muscle_counts.reset_index()).mark_bar().encode(
        x=alt.X('muscle_group:N', title='Muscle Group'),
        y=alt.Y('count:Q', title='Number of Exercises'),
        color=alt.Color('muscle_group:N', legend=None)
    ).properties(
        title='Muscle Group Distribution'
    )
    
    return chart

st.title("📊 Workout Analysis")
if 'username' in st.session_state:
    username = st.session_state.username[0]
    df = load_workout_log(username)

    if df is not None:
        # Add start date to header
        start_date = df['date'].min().strftime('%Y-%m-%d')
        st.write(f"Tracking since: {start_date}")
        # AI Analysis
        st.subheader("WorkoutBot Analysis")

        if st.button("Generate WorkoutBot Analysis"):
            with st.spinner("Analyzing your workout history..."):
                analysis = get_ai_analysis(df)
                st.markdown(analysis)
        
        st.divider()

        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Workouts", len(df))
        with col2:
            st.metric("Unique Exercises", df['exercise_name'].nunique())
        with col3:
            st.metric("Days Active", df['date'].nunique())
        
        # Activity heatmap
        st.subheader("Exercise Activity Over Time")
        activity_chart = create_activity_heatmap(df)
        if activity_chart:
            st.altair_chart(activity_chart, use_container_width=True)
        
        # Workout type and muscle group analysis
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("Workout Types")
            workout_chart = create_workout_type_chart(df)
            if workout_chart:
                st.altair_chart(workout_chart, use_container_width=True)
        
        with col2:
            st.subheader("Muscle Groups")
            muscle_chart = create_muscle_group_chart(df)
            if muscle_chart:
                st.altair_chart(muscle_chart, use_container_width=True)
        
        # exercise history
        st.subheader("Exercise History")
        
        # Search for details
        col1, col2, col3 = st.columns(3)
        with col1:
            workout_types = ['All'] + sorted(df['workout_type'].unique().tolist())
            selected_type = st.selectbox('Filter by Workout Type', workout_types)
        
        with col2:
            muscle_groups = ['All'] + sorted(df['muscle_group'].unique().tolist())
            selected_muscle = st.selectbox('Filter by Muscle Group', muscle_groups)
            
        with col3:
            difficulties = ['All'] + sorted(df['difficulty'].unique().tolist())
            selected_difficulty = st.selectbox('Filter by Difficulty', difficulties)
        
        # filters
        filtered_df = df.copy()
        if selected_type != 'All':
            filtered_df = filtered_df[filtered_df['workout_type'] == selected_type]
        if selected_muscle != 'All':
            filtered_df = filtered_df[filtered_df['muscle_group'] == selected_muscle]
        if selected_difficulty != 'All':
            filtered_df = filtered_df[filtered_df['difficulty'] == selected_difficulty]
        
        # filtered data
        display_columns = [
            'date', 'exercise_name', 'muscle_group', 'workout_type', 'difficulty',
            'lbs/bw_reps for first set', 'lbs/bw_reps for second set', 'lbs/bw_reps for third set'
        ]
        
        st.dataframe(
            filtered_df[display_columns].sort_values('date', ascending=False),
            hide_index=True
        )
        
        # Export your data
        if st.button('Export Exercise History'):
            csv = filtered_df.to_csv(index=False)
            st.download_button(
                label="Download CSV",
                data=csv,
                file_name="exercise_history.csv",
                mime="text/csv"
            )
else:
    st.warning("Please Login to access your analysis")