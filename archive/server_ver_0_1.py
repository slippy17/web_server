from flask import Flask, render_template, request, jsonify
import json
import time 
import os


class Juke():
    def __init__(self):
        self.is_playing = False
        self.cur_disc = 2
        self.cur_track = 1
        self.cur_time = 0
        self.song_len = 0
        self.end = 0
        
    def play(self, disc_indx, track):
        self.cur_disc = disc_indx
        self.cur_track = track
        self.is_playing = True
        self.song_len = int(self.cddb[disc_indx]['disc']['release-list'][0]['medium-list'][0]['track-list'][int(track)]['length'])
        self.end = time.time() + self.song_len
        self.datum = 0
        return 'Playing', self.song_len
    
    def pause(self):
        
        if self.is_playing == True:
            self.datum = time.time()
            self.is_playing = 'Paused'
            return self.is_playing, self.datum
        if self.is_playing == 'Paused':
            offset = int(time.time() - self.datum)
            self.end = self.end + offset
            self.is_playing = True
            return self.is_playing, offset
        return self.is_playing
    
    def get_elaspsed(self):
        if self.is_playing == 'Paused': return self.cur_time * 1000
        self.cur_time = self.song_len - int (self.end - time.time() )
        if self.cur_time> (self.song_len/1000): self.is_playing = False
        if self.is_playing == False: self.cur_time=0
        return self.cur_time * 1000
        
    
    def stop(self):
        self.is_playing = False
        self.cur_time = 0
        return 'Stopped'
    
    def status(self):
        message = {}
        message ['disk'] = self.cur_disc
        message ['song'] = self.cur_track
        message ['length'] = self.song_len
        message ['time'] = self.get_elaspsed()
        message ['is_playing'] = self.is_playing
        return message

    def load(self):
    	with open("./static/cd_database.json", "r") as infile:
            self.cddb = json.load(infile)
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

        


app = Flask(__name__)

player = Juke()
player.load()

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
		print (command, code, raw)
		##os.system("sudo ./pioneer "+ raw)
		time.sleep(1)
	return



@app.route('/init', methods=['GET'])
def init():
	message = player.status()
	return jsonify(message)  # serialize and use JSON headers



@app.route('/')
def home():

    return render_template('index.html')



@app.route('/loadDatabase/<index_no>', methods=['POST','GET'])
def load_DB(index_no):
	data = player.album_stats(index_no)

	return jsonify(data)



##@app.route('/requestSong/<s_cd>/<s_track>', methods=['POST','GET'])
@app.route('/requestSong/', methods=['POST'])
def requestSong():
	if request.method == 'POST':
		
		data = request.json
		s_cd = str(data['Disk'])
		s_track = str(data['Song']+1)
	

		
## Command builder makes list of commands to send.

	c_builder = []

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


	send_code(c_builder)

	print(player.play(s_cd, s_track))


	return '200'



if __name__=="__main__":
	app.run(debug=True, host='192.168.1.114')
	