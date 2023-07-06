from datetime import datetime

import ephem
import humanize
import plotly.graph_objects as go
import pytz
import requests
from discord_webhook import DiscordEmbed, DiscordWebhook  # Connect to discord
from environs import Env  # For environment variables

from SimplePythonSunPositionCalculator import getSEA


def get_next_equinox_or_solstice(lat, long):
    # create an observer object for your location
    observer = ephem.Observer()
    observer.lat = lat
    observer.lon = long

    # get the next equinox and solstice
    next_equinox = (ephem.next_equinox(observer.date).datetime(), "Equinox")
    next_solstice = (ephem.next_solstice(observer.date).datetime(), "Solstice")

    # find which one is closer
    next_event = min([next_equinox, next_solstice], key=lambda x: x[0])

    # calculate and return the time until then
    return next_event


# Setting up environment variables
env = Env()
env.read_env()  # read .env file, if it exists


def format_td(x):
    # convert timedelta to seconds
    total_seconds = x.total_seconds()

    # calculate hours, minutes, and seconds
    hours, remainder = divmod(total_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)

    # float to str with zeropad
    hours = str(int(hours)).zfill(2)
    minutes = str(int(minutes)).zfill(2)
    seconds = str(int(seconds)).zfill(2)

    return f'{hours}:{minutes}:{seconds}'


def iso_to_datetime_str(x):
    # takes a isoformat string
    # then turns it into datetime object
    y = datetime.fromisoformat(x)
    z = y.astimezone(pytz.timezone('US/Eastern'))
    return z.strftime("%H:%M")


lat = float(env("LATITUDE"))
long = float(env("LONGITUDE"))
data = requests.get(
    F"https://api.sunrise-sunset.org/json?lat={lat}&lng={long}&formatted=0").json()['results']

astronomical_twilight_begin = iso_to_datetime_str(
    data['astronomical_twilight_begin'])
sunrise = iso_to_datetime_str(data['sunrise'])
solar_noon = iso_to_datetime_str(data['solar_noon'])
sunset = iso_to_datetime_str(data['sunset'])
astronomical_twilight_end = iso_to_datetime_str(
    data['astronomical_twilight_end'])


def embed_to_discord():
    # create embed object for webhook
    today = datetime.now().astimezone(pytz.timezone('US/Eastern')).strftime("%Y %m %d")
    embed = DiscordEmbed(title=f"Sun Position Today {today}", color="ffff00")

    embed.set_image(url='attachment://fig1.png')

    # add fields to embed
    date_of_event, event_type = get_next_equinox_or_solstice(lat, long)
    embed.add_embed_field(name=f'Next {event_type}', value=humanize.naturaldelta(
        datetime.now() - date_of_event))

    embed.add_embed_field(name='Daylight Length', value=format_td(
        datetime.fromisoformat(data['sunset']) - datetime.fromisoformat(data['sunrise'])))

    # set footer
    embed.set_footer(text='Made By Ibby With ❤️',
                     icon_url='https://avatars.githubusercontent.com/u/22484328?v=4')

    # add embed object to webhook(s)
    for url in env.list("WEBHOOKS"):
        webhook = DiscordWebhook(url=url)

        # image
        with open("fig1.png", "rb") as f:
            webhook.add_file(file=f.read(), filename='fig1.png')

        webhook.add_embed(embed)
        webhook.execute()


# list of angles and their respective times that they happen at
sun_angle_list = []
time_list = []

# calculates the difference in hours between UTC and any timezone in this case US Eastern
utc_offset = datetime.now(pytz.timezone('US/Eastern'))
utc_offset = int(utc_offset.utcoffset().total_seconds()/3600)

for h in range(24):
    for m in range(0, 60):
        angle = getSEA(lat, long, utc_offset, hour=h, minute=m,
                       day_of_year=datetime.now().timetuple()[7])
        sun_angle_list.append(angle)
        time_list.append(f'{h:02}:{m:02}')


fig = go.Figure(data=go.Scatter(
    x=time_list, y=sun_angle_list, mode='lines'))

# makes the background white
fig.update_layout(paper_bgcolor='#fff',
                  plot_bgcolor='#fff')

# Labels
fig.update_layout(title={'text': 'Sun Elevation Angle With Astronomical Twilight & Solar Noon', 'x': 0.5, 'xanchor': 'center'},
                  yaxis_zeroline=True,
                  xaxis_zeroline=True,
                  xaxis_title="Time",
                  yaxis_title="Angle (in Degrees)")

# takes the five important variables and finds their angles by finding the index at which the angles occur
five_variables_time = [astronomical_twilight_begin, sunrise,
                       solar_noon, sunset, astronomical_twilight_end]
five_variables_index = [time_list.index(i) for i in five_variables_time]
five_variables_angles = [sun_angle_list[i] for i in five_variables_index]

# Annotates the five important times on the graph
# the plus 3 is so that the text does not go through the lines
fig.add_trace(go.Scatter(
    x=five_variables_time,
    y=[i + 4 for i in five_variables_angles],
    mode="text",
    text=five_variables_time,
    textfont=dict(
        size=15,
        color="black"
    )
))

# I don't want to show every 15 minute interval because it gets messy
fig.update_xaxes(nticks=12)

# Hides the legend because it includes extraneous information
fig.update_layout(showlegend=False)

# fills in the daytime to be slightly yellow
fig.add_trace(go.Scatter(
              x=[time_list[i] for i in range(
                  five_variables_index[1], five_variables_index[3] + 1)],
              y=[sun_angle_list[i] for i in range(
                  five_variables_index[1], five_variables_index[3] + 1)],
              fill='tozeroy',
              fillcolor="rgba(255, 255, 51, 0.1)",
              mode='none'
              ))

# these two fills in both before and after daylight to be slightly dark
# this is for midnight to sunrise
fig.add_trace(go.Scatter(
              x=[time_list[i] for i in range(0, five_variables_index[1] + 1)],
              y=[sun_angle_list[i]
                  for i in range(0, five_variables_index[1] + 1)],
              fill='tozeroy',
              fillcolor='rgba(0, 0, 51, 0.1)',
              mode='none'
              ))
# this is for sunset to midnight
fig.add_trace(go.Scatter(
              x=[time_list[i] for i in range(
                  five_variables_index[3], len(time_list))],
              y=[sun_angle_list[i]
                  for i in range(five_variables_index[3], len(time_list))],
              fill='tozeroy',
              fillcolor='rgba(0, 0, 51, 0.1)',
              mode='none'
              ))

fig.write_image("fig1.png", width=1920, height=1080)
embed_to_discord()
