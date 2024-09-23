import os
import argparse
import psycopg2
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError
from datetime import datetime, timedelta

# Configuration
SLACK_TOKEN = os.getenv("SLACK_API_TOKEN")
CHANNELS = os.getenv("SLACK_CHANNEL_IDS").split(',')

# Database connection
def get_db_connection():
    return psycopg2.connect(
        dbname=os.getenv("PG_DB"),
        user=os.getenv("PG_USER"),
        password=os.getenv("PG_PW"),
        host="postgres",  # Use the name of the PostgreSQL container
        port="5432"
    )

# Fetch messages from Slack
def fetch_messages(client, channel_id, oldest):
    all_messages = []
    try:
        while True:
            response = client.conversations_history(channel=channel_id, oldest=oldest, limit=200)
            messages = response.get('messages', [])
            all_messages.extend(messages)
            if not response['has_more']:
                break
            time.sleep(1)
    except SlackApiError as e:
        print(f"Error fetching messages: {e.response['error']}")
    return all_messages

# Fetch users and channels
def fetch_users_and_channels(client):
    try:
        users = client.users_list()
        channels = client.conversations_list(types="public_channel,private_channel")
        return users['members'], channels['channels']
    except SlackApiError as e:
        print(f"Error fetching users or channels: {e.response['error']}")
        return [], []

# Insert messages into the database
def insert_messages(conn, messages, channel_id):
    with conn.cursor() as cursor:
        for message in messages:
            if 'user' in message:  # Ensure there's a user associated with the message
                cursor.execute("""
                    INSERT INTO messages (channel_id, user_id, content, timestamp)
                    VALUES (
                        (SELECT id FROM channels WHERE slack_channel_id = %s),
                        (SELECT id FROM users WHERE slack_user_id = %s),
                        %s,
                        %s
                    )
                    ON CONFLICT (timestamp) DO UPDATE SET
                    content = EXCLUDED.content
                """, (channel_id, message['user'], message['text'], message['ts']))
        conn.commit()

# Insert users into the database
def insert_users(conn, users):
    with conn.cursor() as cursor:
        for user in users:
            cursor.execute("""
                INSERT INTO users (slack_user_id, name)
                VALUES (%s, %s)
                ON CONFLICT (slack_user_id) DO NOTHING
            """, (user['id'], user['name']))
        conn.commit()

# Insert channels into the database
def insert_channels(conn, channels):
    with conn.cursor() as cursor:
        for channel in channels:
            cursor.execute("""
                INSERT INTO channels (slack_channel_id, name)
                VALUES (%s, %s)
                ON CONFLICT (slack_channel_id) DO NOTHING
            """, (channel['id'], channel['name']))
        conn.commit()

# Main function
def main(days_back):
    client = WebClient(token=SLACK_TOKEN)

    conn = get_db_connection()

    # Fetch users and channels
    users, channels = fetch_users_and_channels(client)
    insert_users(conn, users)
    insert_channels(conn, channels)

    # Fetch and insert messages for each channel
    since_date = (datetime.now() - timedelta(days=days_back)).timestamp()
    for channel in CHANNELS:
        print(f"Fetching messages from channel: {channel}")
        messages = fetch_messages(client, channel, since_date)
        insert_messages(conn, messages, channel)
        print(f"Inserted {len(messages)} messages from channel {channel}")

    conn.close()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description='Fetch messages from Slack and update the database.')
    parser.add_argument('--days-back', type=int, default=7, help='Number of days back to fetch messages from (default: 7).')
    args = parser.parse_args()
    
    main(args.days_back)