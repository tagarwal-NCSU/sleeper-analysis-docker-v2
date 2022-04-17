from flask import Flask, request, url_for, render_template, redirect, flash
import dash
import os
import requests
import pandas as pd
import json
import plotly
import plotly.express as px
from dash import dcc, html
import numpy as np

# Visualization Example Here:
# https://towardsdatascience.com/web-visualization-with-plotly-and-flask-3660abf9c946

server = Flask(__name__)
app = dash.Dash(__name__, server=server, url_base_pathname="/null/")
app.layout = html.Div()

URL = "https://api.sleeper.app/v1/players/nfl"
response = requests.get(URL)
PLAYER_DICTIONARY = response.json()

# Create a list of all stats that need to be fetched

# These come from the Player dictionary, and must be explicitly added to the loop @ **Position 1**
identifiers = ["Owner", "Week", "Player", "player_id", "age", "position"]

# These will automatically be added to the stats
default_stats = ["gp", "off_snp", "tm_off_snp", "pts_ppr", "pts_half_ppr", "pts_std"]
rush_stats = ["rush_att", "rush_yd", "rush_yac", "rush_rz_att", "rush_td"]
rec_stats = ["rec_tgt", "rec", "rec_yd", "rec_yar", "rec_rz_tgt", "rec_td"]
pass_stats = ['pass_att', 'pass_yd', 'pass_cmp', 'pass_rz_att', 'pass_2pt', 'pass_int', 'pass_sack_yds', 'pass_td']
kick_stats = ['xpm', 'xpa', 'fgm', 'fga']
def_stats = ['sacks', 'fum_rec', 'int', 'def_td', 'yds_allow', 'pts_allow', 'blk_kick']
fumble_stats = ['fum', 'fum_lost']

stat_list = default_stats + rush_stats + rec_stats + pass_stats + def_stats + fumble_stats

@server.context_processor #allows CSS to update (bypass browser cache)
def override_url_for():
    return dict(url_for=dated_url_for)

def dated_url_for(endpoint, **values):
    if endpoint == 'static':
        filename = values.get('filename', None)
        if filename:
            file_path = os.path.join(server.root_path,
                                 endpoint, filename)
            values['q'] = int(os.stat(file_path).st_mtime)
    return url_for(endpoint, **values)

@server.route("/")
def home():
    return render_template("home.html")

@server.route("/about")
def about():
    return render_template("about.html")

@server.route("/contact")
def contact():
    return render_template("contact.html")

@server.route("/leagues")
def leagues():
    # find user's sleeper username
    username = request.args.get('username', "-")
    URL = f"https://api.sleeper.app/v1/user/{username}"

    # find their corresponding sleeper user id    
    response = requests.get(URL)
    if response.status_code != 200: #If the username is invalid
        flash('That username is invalid')
        return redirect(url_for(''))
    user_id = response.json()
    user_id = user_id['user_id']

    # set season to 2021 to look at last year's response
    season = '2021'
    sport = 'nfl' #only sport currently possible for this API
    URL = f"https://api.sleeper.app/v1/user/{user_id}/leagues/{sport}/{season}"
    response = requests.get(URL)
    leagues = response.json()

    # create loop to pull out just their league names
    total_leagues = len(leagues) # find length of their #of leagues by looking at number of items within their leagues object
    if total_leagues > 5:
        height = 5
        width = total_leagues % 5
    else:
        height = total_leagues
        width = 1
    league_ids = [league['league_id'] for league in leagues]
    league_names = [league['name'] for league in leagues]
    return render_template("leagues.html", 
                            total_leagues = total_leagues, 
                            league_ids = league_ids, 
                            league_names = league_names,
                            username = username)

@server.route("/viz")
def viz():
    league_id = request.args.get('league_id', "-")
    username = request.args.get('username', "-")
    league_name = request.args.get('league_name', "-")
    if str(league_id) == "-":
        return redirect(f'/leagues?username={username}')

    stats = fetch_data(league_id)

    URL = f"https://api.sleeper.app/v1/league/{league_id}"
    response = requests.get(URL)
    league_info = response.json()
    ppr = league_info['scoring_settings']['rec']
    if ppr == 1.0:
        scoring_type = "PPR "
        point_settings = "pts_ppr"
    elif ppr == 0.5:
        scoring_type = "Half PPR "
        point_settings = "pts_half_ppr"
    else:
        scoring_type = ""
        point_settings = "pts_std"


    scale = "sunsetdark"

    
    position = "RB"

    avg_age_position = get_avg_age_position(stats)
    avg_age_overall = get_avg_age_overall(stats, scale)
    player_line_graphs = get_player_line_graphs(stats, username)
    POS_YPC_YPR, POS_TD, POS_PPG, POS_YPG = get_pos_stats(stats, username, point_settings, scale, position)
    PPG = get_PPG(stats, username, point_settings, scale)

    app.title = f"{league_name} - Pillow"
    app.layout = html.Div(children = [
        html.Header(
        html.Nav(children = [
                    html.Ul(children = [
                        html.Li(html.A(html.Img(src=url_for('static',filename='pillow.png'), className="logo"), href="/")),
                        # html.Li(html.A("About", href="/about")),
                        # html.Li(html.A("Contact", href="/contact"))
                    ])
        ])
        ),
        
        html.Br(),
        html.H1(league_name, style={'text-align': 'center'}),
        html.P(f"*Point values shown are based on standard {scoring_type}scoring settings"),

        html.Div(children=[
            dcc.Graph(
                id = 'example',
                figure = avg_age_position
                ),
        ], style={'display': 'inline'}
        ),
        html.Div(children=[
            dcc.Graph(
                id = 'example',
                figure = avg_age_overall
                ),
        ]
        ),

        html.Div(children=[
            dcc.Graph(
                id = 'example',
                figure = player_line_graphs
                ),
        ]
        ),
        html.Div(children=[
            dcc.Graph(
                id = 'example',
                figure = PPG
                ),
        ]
        ),

        html.Div(children=[
            dcc.Graph(
                id = 'example',
                figure = POS_YPC_YPR
                ),
        ]
        ),
        html.Div(children=[
            dcc.Graph(
                id = 'example',
                figure = POS_TD
                ),
        ]
        ),

        html.Div(children=[
            dcc.Graph(
                id = 'example',
                figure = POS_PPG
                ),
        ]
        ),
        html.Div(children=[
            dcc.Graph(
                id = 'example',
                figure = POS_YPG
                ),
        ]
        ),
    ], style={'text-align': 'center'})
    # Render template
    return app.index()

def fetch_data(league_id):
    # Fetch League Metadata
    URL = f"https://api.sleeper.app/v1/league/{league_id}"
    response = requests.get(URL)
    league = response.json()

    # Fetch infomation about users in the league
    URL = f"https://api.sleeper.app/v1/league/{league_id}/users"
    response = requests.get(URL)
    users = response.json()

    # Fetch information about current rosters in the league
    URL = f"https://api.sleeper.app/v1/league/{league_id}/rosters"
    response = requests.get(URL)
    rosters = response.json()

    # Get league name and league season
    league_name = league['name']
    season = league['season']
    playoff_week = league['settings']['playoff_week_start']

    # Create a lookup dictionary connecting owner usernames to their roster players
    owner_players = [[PLAYER_DICTIONARY[player_id] for player_id in roster['players']] for roster in rosters]
    owner_ids = [roster['owner_id'] for roster in rosters]
    ownerid2name = {owner['user_id']: owner['display_name'] for owner in users}
    owner2players = {ownerid2name[owner_ids[i]]: owner_players[i] for i in range(len(owner_ids))}
    
    # Initialize the Dataframe
    df = []

    # For each week in the regular season...
    for week in range(1, playoff_week+1):
        # Extract player stats for that week
        URL = f"https://api.sleeper.app/v1/stats/nfl/regular/{season}/{week}"
        response = requests.get(URL)
        stats = response.json()
        # For each player in owners' rosters...
        for owner, players in owner2players.items():
            for player in players:
                # Extract identifiers for the current player
                player_id = player['player_id']
                if 'age' in player:
                    player_age = player['age']
                else:
                    player_age = np.nan
                player_name = player['first_name'] + ' ' + player['last_name']
                player_position = player['position']
                # **Position 1**
                row = [owner, week, player_name, player_id, player_age, player_position]
                # Extract stats for the player, if they played that week
                if player_id in stats:
                    player_stats = stats[player_id]
                    # If the stat exists in player stats, extract the stat, otherwise put NaN
                    row += [player_stats[stat] if stat in player_stats else np.nan for stat in stat_list]
                # If the player did not play that week
                else:
                    # Make the entire row NaN
                    row += [np.nan] * len(stat_list)
                # Add the row to the Dataframe
                df.append(row)

    #Build the Dataframe
    columns = identifiers + stat_list
    df = pd.DataFrame(df, columns = columns)

    # Extract season-long stats
    URL = f"https://api.sleeper.app/v1/stats/nfl/regular/{season}"
    response = requests.get(URL)
    stats = response.json()

    # Initialize the Dataframe
    df_season = []

    # For each player in owners' rosters...
    for owner, players in owner2players.items():
        for player in players:
            # Extract identifying information
            player_id = player['player_id']
            if 'age' in player:
                player_age = player['age']
            else:
                player_age = np.nan
            player_name = player['first_name'] + ' ' + player['last_name']
            player_position = player['position']
            row = [owner, "Season", player_name, player_id, player_age, player_position]
            if player_id in stats:
                player_stats = stats[player_id]
                row += [player_stats[stat] if stat in player_stats else np.nan for stat in stat_list]
            else:
                row += [np.nan] * len(stat_list)
            df_season.append(row)

    # Build the Dataframe
    df_season = pd.DataFrame(df_season, columns = columns)

    stats = pd.concat([df, df_season])

    return stats

def get_avg_age_position(stats):
    age2 = stats[stats["Week"] == "Season"][["Owner", "age", "position", "Week"]]
    age2 = age2.groupby(["Owner", "position"]).agg({"age": np.mean})
    age2 = age2.reset_index()
    fig = px.bar(age2, y = "age", x = "Owner", color = "position", barmode = "group")
    fig.update_layout(xaxis={'categoryorder':'total ascending'})
    fig.update_yaxes(range = [18,45])
    fig.update_layout(title_text="Average Age by Position", title_x=0.5)
    fig.update_layout(
        font_family="Times New Roman",
        font_color="black",
        title_font_family="Times New Roman",
        title_font_color="blue",
        title_font_size=24
    )
    return fig

def get_avg_age_overall(stats, scale):
    avg_age = stats[stats["Week"] == "Season"].age.mean()
    age = pd.DataFrame(stats[stats["Week"] == "Season"].groupby("Owner").agg({"age": np.mean}))
    scale = "sunsetdark"
    fig = px.bar(age, x = "age", color = 'age', color_continuous_scale=scale) #can drop color option, but I like how it ranks everyone's age and shows a clear legend

    fig.add_vline(x=avg_age)
    fig.update_layout(yaxis={'categoryorder':'total descending'})
    fig.update_xaxes(range = [18,30])
    fig.update_layout(title_text="Average Team Age by Owner", title_x=0.5)
    fig.update_layout(
        font_family="Times New Roman",
        font_color="black",
        title_font_family="Times New Roman",
        title_font_color="blue",
        title_font_size=24
    )
    return fig

def get_player_line_graphs(stats, username):
    users_stats = stats[stats["Owner"] == username]
    users_wkly_stats = users_stats[users_stats["Week"] != "Season"]

    fig = px.line(users_wkly_stats, x = "Week", y = "pts_half_ppr", facet_col = "Player", facet_col_wrap=4, height=1500)
    fig.update_layout(title_text=f"{username}'s Player Trends Throughout the Year", title_x=0.5)
    fig.update_layout(
        font_family="Times New Roman",
        font_color="black",
        title_font_family="Times New Roman",
        title_font_color="blue",
        title_font_size=24
    )
    return fig

def get_PPG(stats, username, point_settings, scale):
    #ppg stats for all players on your team
    users_stats = stats[stats["Owner"] == username]
    user_szn_stats = users_stats[users_stats['Week'] == 'Season'].copy()
    user_szn_stats['ppg'] = user_szn_stats[point_settings] / user_szn_stats['gp']
    ppg = user_szn_stats[['Player', 'ppg']]
    ppg = ppg.set_index('Player')
    fig = px.imshow(ppg, text_auto = True, aspect = "auto", color_continuous_scale=scale, height=700)
    fig.update_layout(title_text=f"{username}'s Player's Points Per Game", title_x=0.5)
    fig.update_layout(
        font_family="Times New Roman",
        font_color="black",
        title_font_family="Times New Roman",
        title_font_color="blue",
        title_font_size=24
    )
    return fig

def get_pos_stats(stats, username, point_settings, scale, position):
    # Feature to be added later - Use other positions
    # position = "QB", "WR", etc
    #create dataframes that can filter by owner, then season, and then by position
    pos_stats = stats[(stats["Owner"] == username) & (stats['Week'] == 'Season') & (stats["position"] == position)].copy()

    #calculate desired stats
    pos_stats['ypc'] = round(pos_stats['rush_yd'] / pos_stats['rush_att'], 2)

    pos_stats['ypr'] = round(pos_stats['rec_yd'] / pos_stats['rec'], 2)

    pos_stats['rush_tds_per_game'] = round(pos_stats['rush_td'] / pos_stats['gp'], 3)
    #if they never had a rush td set it to 0
    pos_stats['rush_tds_per_game'] = np.where(pos_stats['rush_tds_per_game'].isnull(), 0, pos_stats['rush_tds_per_game'])

    pos_stats['rec_tds_per_game'] = round(pos_stats['rec_td'] / pos_stats['gp'], 3)
    #if they never had a rec td set it to 0
    pos_stats['rec_tds_per_game'] = np.where(pos_stats['rec_tds_per_game'].isnull(), 0, pos_stats['rec_tds_per_game'])

    pos_stats['ppg'] = round(pos_stats[point_settings] / pos_stats['gp'], 2)

    #separate stats into two dif dfs for heatmap visualization
    pos_stats1 = pos_stats[['Player', 'ypc', 'ypr']]
    pos_stats1 = pos_stats1.set_index('Player')
    pos_stats2 = pos_stats[['Player', 'rush_tds_per_game', 'rec_tds_per_game']]
    pos_stats2 = pos_stats2.set_index('Player')

    POS_YPC_YPR = px.imshow(pos_stats1, text_auto = True, aspect = "auto", color_continuous_scale=scale)
    POS_YPC_YPR.update_layout(title_text=f"{username}'s RB's Yards Per Carry and Yards Per Reception", title_x=0.5)
    POS_YPC_YPR.update_layout(
        font_family="Times New Roman",
        font_color="black",
        title_font_family="Times New Roman",
        title_font_color="blue",
        title_font_size=18
    )

    POS_TD = px.imshow(pos_stats2, text_auto = True, aspect = "auto", color_continuous_scale=scale)
    POS_TD.update_layout(title_text=f"{username}'s RB's TD's Per Game", title_x=0.5)
    POS_TD.update_layout(
        font_family="Times New Roman",
        font_color="black",
        title_font_family="Times New Roman",
        title_font_color="blue",
        title_font_size=18
    )
    POS_TD.update_layout(showlegend=False)

    avg_ppg = pos_stats.ppg.mean()
    POS_PPG = px.bar(pos_stats, x = 'Player', y = 'ppg', color = 'ppg', text = 'ppg')
    POS_PPG.add_hline(y=avg_ppg)
    POS_PPG.update_layout(title_text=f"{username}'s RB's Points Per Game", title_x=0.5)
    POS_PPG.update_layout(
        font_family="Times New Roman",
        font_color="black",
        title_font_family="Times New Roman",
        title_font_color="blue",
        title_font_size=24
    )
    POS_PPG.update_layout(showlegend=False)

    pos_stats['tot_ypg'] = round((pos_stats['rec_yd'] + pos_stats['rush_yd']) / pos_stats['gp'], 2)
    tot_ypg = round(pos_stats.tot_ypg.mean(), 1)

    POS_YPG = px.bar(pos_stats,x = 'Player', y = 'tot_ypg', color = 'tot_ypg', text = 'tot_ypg', color_continuous_scale=scale)
    POS_YPG.add_hline(y=tot_ypg)
    POS_YPG.update_layout(title_text=f"{username}'s RB's YPG", title_x=0.5)
    POS_YPG.update_layout(
        font_family="Times New Roman",
        font_color="black",
        title_font_family="Times New Roman",
        title_font_color="blue",
        title_font_size=24
    )

    return POS_YPC_YPR, POS_TD, POS_PPG, POS_YPG

server.run()