from threading import Event, Thread
from flask import Flask, render_template, request, jsonify
import json
import time 
import os
import pandas as pd
import playtime as pt

# Environment variables.
ip_addr= os.environ['IP_ADDRESS']

gpio_avail= eval(os.environ['GPIO_AVAIL'])

print (f"IP ADDRESS {ip_addr} GPIO_AVAIL is {gpio_avail}")

if gpio_avail : os.system("sudo ./ledON")




class Juke():

    playtimer = pt.Tmr()


    def __init__(self):
        self.is_playing = 0
        self.cur_disc = 40
        self.cur_track = 1
        self.cur_time = 0
        self.song_len = 0   
        self.end = 0        ## Time that songs ends.
        
        
        
    def call_repeatedly(self,interval, func, *args):
        stopped = Event()
        def loop():
            while not stopped.wait(interval): # the first call is in `interval` secs
                func(*args)
        Thread(target=loop).start()    
        return stopped.set        



    def play(self, disc_indx, track):
        self.cur_disc = disc_indx
        self.cur_track = track
        self.is_playing = 1
        #self.song_len = 10#int(player.cddb[str(disc_indx)]['disc']['release-list'][0]['medium-list'][0]['track-list'][track-1]['length'])/1000

        x = self.df[(self.df["Disc_ID"] == self.cur_disc) & (self.df["Track_ID"] == self.cur_track)]
        self.song_len = int(x.Length/1000)
        print(x)
        
        print(f'*********** Song Length is {int(self.song_len)} seconds')
        Juke.playtimer.run(int(self.song_len))
        self.cancel_future_calls = self.call_repeatedly(5, self.check_timer)

        return 'Playing', self.song_len


    def check_timer(self):
        if Juke.playtimer.remaining == 0:
            self.stop()
            return
        return

    
 

    def pause(self):
        if self.is_playing == 1:
            self.is_playing = -1
            Juke.playtimer.pause()
            send_code(['Pause'])
            return self.is_playing, Juke.playtimer.remaining

        if self.is_playing == -1:
            self.is_playing = 1
            Juke.playtimer.resume()
            send_code(['Resume'])
            return self.is_playing

        return self.is_playing
        
  
        
    def stop(self):
        self.is_playing = 0
        self.cur_time = 0
        self.cancel_future_calls()
        send_code(['Stop'])
        return 'Stop'


    def status(self):
        message = {}
        message['disk'] = self.cur_disc
        message['song'] = self.cur_track
        message['length']= self.song_len
        message['time'] = Juke.playtimer.elap
        message['is_playing'] = self.is_playing
        return message

    def load(self):
    	with open("./static/cd_database.json", "r") as infile:
            self.cddb = json.load(infile)
            return

    def load_df(self):
        self.df= pd.read_pickle("./static/cd_database.pkl")
        self.df.Length = self.df.Length.astype('int32')
        self.df.Disc_ID = self.df.Disc_ID.astype('int')
        self.adf= self.df[['Album', 'Disc_ID', 'Artist']].copy()
        self.adf= self.adf.drop_duplicates(subset=['Album'], ignore_index=True)
        return
    
    def album_stats(self,index_no):
    	db = self.cddb[index_no]['disc']['release-list'][0]
    	message = []
    	tracks = db['medium-list'][0]['track-count']
    	track_list = db['medium-list'][0]['track-list']
    	artist =  db['artist-credit'][0]['artist']['name']
    	album = db['title'] 	
    	message.append({'tracks':tracks})
    	message.append(track_list)
    	message.append({'artistname':artist})
    	message.append({'album':album})
    	return message

    def album_stats_df(self,index_no):  ## ************** TESTED ************
        db = self.adf.loc[index_no]
        d_id = db.Disc_ID
        tracks_df = self.df[self.df["Disc_ID"] == d_id]
        tracks_df = tracks_df.sort_values(by=['Track_ID'], ignore_index=True)
           ## Album info for the album at that Disc_ID.
        tracks = tracks_df.Song_Title.count()   ## The number 0f tracks in the album
        return tracks_df

        


app = Flask(__name__)

player = Juke()
#player.load()
player.load_df()




#cur_disk = 10
#cur_song = 5
#cur_song_len = 0
#cur_time = 0
#is_playing = False


def send_code(commands):
	with open("./static/p_codes.json", "r") as infile:
		cd_player = json.load(infile)
	for command in commands:
            code = (cd_player[command])
            raw = bin(int(code, 16))[2:].zfill(32)
            if command == 'Play':
                time.sleep(6)
            print (command, code)
            if gpio_avail : os.system("sudo ./pioneer "+ raw)
            time.sleep(0.6)
	return



@app.route('/stat', methods=['POST', 'GET'])
def init():
	stat = player.status()
	return jsonify(stat)  # serialize and use JSON headers



@app.route('/pause', methods=['GET'])
def  pause_request():
    message = player.pause()
    return jsonify(message)  # serialize and use JSON headers


# @app.route('/resume', methods=['GET'])
# def  pause_request():
#     message = player.resume()
#     return jsonify(message)  # serialize and use JSON headers


@app.route('/')
def home():
    
    return render_template('index.html')


@app.route('/loadDatabase/<index_no>', methods=['GET','POST'])
def load_DB(index_no):
	index_no = int(index_no)
	data = player.album_stats_df(index_no) ## changed from .ablum_stats
	
	data = data.to_dict( orient="records")
	#print (f'*********************** {type(data)} *******************************')
	#with open("data.json", "w") as outfile:
	#	json.dump(data,outfile,indent=2)

	return jsonify(data)



##@app.route('/requestSong/<s_cd>/<s_track>', methods=['POST','GET'])
@app.route('/requestSong/', methods=['POST'])
def requestSong():
	if request.method == 'POST':
		
		data = request.json
		s_idx = data['Index']  ## Index from the client.
		s_cd = str(player.adf.loc[s_idx].Disc_ID) ## Lookup the Disc_ID from that Index.
		s_track = str(data['Song']+1)
	

		
## Command builder makes list of commands to send.

	c_builder = ['Pause']

	if (int(s_cd)>100) or (len(s_track)>2):
	    print("Error in the length of numbers")

	a1= s_cd[0]
	c_builder.append(a1)
	
	if len(s_cd) == 2:
	    a2= s_cd[1]
	    c_builder.append(a2)
	    
	if len(s_cd) == 3:
	    a2= s_cd[1]
	    c_builder.append(a2)
	    a3 = s_cd[2]
	    c_builder.append(a3)
    
    
	c_builder.append('Disc')
	b1= s_track[0]
	c_builder.append(b1)
	if len(s_track) == 2:
	    b2= s_track[1]
	    c_builder.append(b2)
	c_builder.append('Track')

	c_builder.append('Play')


	send_code(c_builder)

	print(player.play(int(s_cd), int(s_track)))


	return '200'



if __name__=="__main__":
	app.run(debug=True, host=ip_addr)
	
