from flask import Flask, jsonify
from flask_socketio import SocketIO, emit, join_room, leave_room
import pyaudio
from cryptography.fernet import Fernet
from flask_cors import CORS  # Import CORS

app = Flask(__name__)
CORS(app)  # Enable CORS for the app
socketio = SocketIO(app, cors_allowed_origins="*")

# Audio settings
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 44100
CHUNK = 1024

# Encryption setup
key = Fernet.generate_key()
cipher_suite = Fernet(key)

# Client tracking
clients = {}
client_id_counter = 1

# Audio communication
rooms = {}

# Flask route to get encryption key
@app.route('/get_key', methods=["GET"])
def get_key():
    return jsonify({'key': key.decode('utf-8')})

# When a new client connects
@socketio.on('connect')
def handle_connect():
    global client_id_counter
    client_id = client_id_counter
    clients[client_id] = {'sid': request.sid}
    client_id_counter += 1
    emit('client_number', {'client_number': client_id})

# Handle client disconnecting
@socketio.on('disconnect')
def handle_disconnect():
    for client_id, data in clients.items():
        if data['sid'] == request.sid:
            del clients[client_id]
            break

# Handle dialing another client
@socketio.on('dial')
def handle_dial(data):
    caller_id = data['caller_id']
    receiver_id = data['receiver_id']
    
    if receiver_id in clients:
        caller_room = f"room_{caller_id}_{receiver_id}"
        join_room(caller_room)
        rooms[caller_id] = receiver_id
        rooms[receiver_id] = caller_id
        emit('dial_success', {'room': caller_room}, room=clients[caller_id]['sid'])
        emit('incoming_call', {'from': caller_id}, room=clients[receiver_id]['sid'])
    else:
        emit('dial_failed', {'error': 'Client does not exist'}, room=request.sid)

# Handle audio transmission between clients
@socketio.on('send_audio')
def handle_audio(data):
    caller_id = data['client_id']
    encrypted_audio = data['audio']
    
    if caller_id in rooms:
        receiver_id = rooms[caller_id]
        emit('receive_audio', {'audio': encrypted_audio}, room=clients[receiver_id]['sid'])

if __name__ == '__main__':
    socketio.run(app, host='0.0.0.0', port=5000)
