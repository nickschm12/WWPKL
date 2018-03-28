from yahoo_oauth import OAuth2
import json
import xmltodict
import pandas as pd

def get_input(prompt,valid_args):
    while True:
        try:
            value = raw_input(prompt)
        except ValueError:
            print("Can't handle that kind of input, try again.")
            continue
        if value not in valid_args:
            print("Invalid input, try again.")
            continue
        else:
            break
    return value

def query_yahoo(url):
    xml_response = oauth.session.get(url)
    json_response = json.dumps(xmltodict.parse(xml_response.content))
    return json.loads(json_response)

def get_wwp_keeper_leagues(url):
    fantasy_content_data = query_yahoo(url)
    seasons = fantasy_content_data['fantasy_content']['users']['user']['games']['game']

    wwp_keeper_leagues = []
    for season in seasons:
        for league in season['leagues']['league']:
            if type(league) is dict:
                league_name = league['name'].encode('utf-8').strip()
                if 'WWP Keeper' in league_name:
                    new_league = {
                                     'key' : league['league_key'].encode('utf-8').strip(),
                                     'name' : league_name,
                                     'year' : league['season'].encode('utf-8').strip(),
                                     'num_teams' : league['num_teams'].encode('utf-8').strip()
                                  }
                    wwp_keeper_leagues.append(new_league)
    return wwp_keeper_leagues

def get_team_stats(url):
    stat_ids = {
      '7' : 'R',
      '8' : 'H',
      '12' : 'HR',
      '13' : 'RBI',
      '16' : 'SB',
      '3' : 'AVG',
      '55' : 'OPS',
      '50' : 'IP',
      '28' : 'W',
      '29' : 'L',
      '32' : 'SV',
      '42' : 'SO',
      '48' : 'HLD',
      '26' : 'ERA',
      '27' : 'WHIP',
      '60' : 'N/A'
    }

    fantasy_content_data = query_yahoo(url)
    team_info = fantasy_content_data['fantasy_content']['team']
    team_name = team_info['name']
    team_id = team_info['team_id']
    team_stats = team_info['team_stats']['stats']['stat']

    stats = [team_name]
    for stat in team_stats:
        if stat_ids[stat['stat_id']] != 'N/A' and stat_ids[stat['stat_id']] != 'IP':
            stats.append(stat['value'])

    return stats

def calculate_roto_standings(df):
    stat_names = ['R', 'H', 'HR', 'RBI', 'SB', 'AVG', 'OPS', 'W', 'L', 'SV', 'SO', 'HLD', 'ERA', 'WHIP']
    batting_ranks = ['R_rank','H_rank','HR_rank','RBI_rank','SB_rank','AVG_rank','OPS_rank']
    pitching_ranks = ['W_rank','L_rank','SV_rank','SO_rank','HLD_rank','ERA_rank','WHIP_rank']

    for stat in stat_names:
        key = str.format('{0}_rank', stat)

        if key in ['L','ERA','WHIP']:
            df[key] = df[stat].rank(ascending=False)
        else:
            df[key] = df[stat].rank()

    df['Batting Total Rank'] = df[batting_ranks].sum(axis=1)
    df['Pitching Total Rank'] = df[pitching_ranks].sum(axis=1)
    df['Total Rank'] = df[['Batting Total Rank','Pitching Total Rank']].sum(axis=1)

    final_df = df[['Team','R','H','HR','RBI','SB','AVG','OPS','Batting Total Rank','W','L','SV','SO','HLD','ERA','WHIP','Pitching Total Rank','Total Rank']]
    return final_df.sort_values(['Total Rank'],ascending=[0])

# main program
oauth = OAuth2(None, None, from_file='oauth2.json')
if not oauth.token_is_valid():
    oauth.refresh_access_token()

base_url = "https://fantasysports.yahooapis.com/fantasy/v2"
wwp_keeper_leagues_url = str.format('{0}/users;use_login=1/games;game_codes=mlb/leagues',base_url)
leagues = get_wwp_keeper_leagues(wwp_keeper_leagues_url)

year = get_input("Which season? (2015, 2016, 2017, 2018) ", ['2015', '2016', '2017', '2018'])
league_key = ''
teams = 0

for league in leagues:
    if league['year'] == year:
        league_key = league['key']
        teams = league['num_teams']

column_headers = ['Team', 'R', 'H', 'HR', 'RBI', 'SB', 'AVG', 'OPS', 'W', 'L', 'SV', 'SO', 'HLD', 'ERA', 'WHIP']

league_stats = []
for team_id in range(1, int(teams) + 1):
    team_stats_url = str.format('{0}/team/{1}.t.{2}/stats',base_url,league_key, team_id)
    team = get_team_stats(team_stats_url)
    league_stats.append(team)

standings = calculate_roto_standings(pd.DataFrame(league_stats, columns=column_headers))

output_csv = get_input("Do you want to create a .csv? (Y/N)", ['Y','N'])
if output_csv == 'Y':
    path = str.format("Standings/{0}_standings.csv", year)
    standings.to_csv(path, sep=',')

print standings
