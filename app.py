# Importing os to traverse files
import os

# Importing pyaudio to record and play audio
import pyaudio

# Import pynput to use the keyboard listener
from pynput import keyboard

# Import time for the use of the sleep function
import time

# Use of multi threading to record audio while the keyboard listens
import threading

# Use of the wave library to save audio files in the .wav file format
import wave

# Use of the openai library to use the ChatGPT and Whisper API
import openai

# Use of the Google Text to Speech API to synthesize a audible response
from google.cloud import texttospeech

# Global variable to indicate whether recording should occur across threads
record = False

def main():
    # Set the API key for the OpenAI API
    # ENTER PERSONAL API KEY HERE
    openai.api_key = ''

    # Set an event for a thread to stop recording if triggered
    stop_recording_event = threading.Event()
    record_audio(stop_recording_event)

    # 2 second buffer to allow for the recording to finish and the file to be saved
    time.sleep(2)

    # Pass in the current working directory to the transcribe function
    # to access the audio file previously generated
    print("Transcribing Audio.....")
    transcript = transcribe(str(os.path.dirname(os.path.realpath(__file__)) + "\\output.wav"))
    
    # Delete the file once it has been transcribed
    os.remove("output.wav")

    # Convert the json format from Whisper to a string
    audio_text = convert_json(transcript)
    print(audio_text)

    # Generate a response from the ChatGPT API
    print("Generating Response.....")
    response = generate_response(audio_text)
    print(response)

    # Synthesize the response into an audio file
    text_to_speech(response)

    # Play the audio file
    play_audio()

    # Delete the audio file once it has been played
    os.remove("final.wav")

# Uses the pyaudio library to play a .wav file.
# Implementation taken from the pyaudio documentation
# https://people.csail.mit.edu/hubert/pyaudio/
def play_audio():
    CHUNK = 1024

    with wave.open('final.wav', 'rb') as wf:
        # Instantiate PyAudio and initialize PortAudio system resources (1)
        p = pyaudio.PyAudio()

        # Open stream (2)
        stream = p.open(format=p.get_format_from_width(wf.getsampwidth()),
                        channels=wf.getnchannels(),
                        rate=wf.getframerate(),
                        output=True)

        # Play samples from the wave file (3)
        while len(data := wf.readframes(CHUNK)):  # Requires Python 3.8+ for :=
            stream.write(data)

        # Close stream (4)
        stream.close()

        # Release PortAudio system resources (5)
        p.terminate()

# Use the Google Text to Speech API to convert the string text to
# an audio file to be played
# Implementation of the Google Text to Speech API based off of the Google Cloud
# documentation
# https://cloud.google.com/text-to-speech/docs/libraries#client-libraries-install-python
#
# Preconditions: Google Cloud SDK must be installed and environment set up,
# and the Google ADB credentials must be set up
def text_to_speech(transcript):
    client = texttospeech.TextToSpeechClient()
    synthesis_input = texttospeech.SynthesisInput(text=transcript)
    voice = texttospeech.VoiceSelectionParams(
        language_code="en-US", ssml_gender=texttospeech.SsmlVoiceGender.NEUTRAL
    )
    audio_config = texttospeech.AudioConfig(
        audio_encoding="LINEAR16",
        sample_rate_hertz=16000,
    )
    response = client.synthesize_speech(
        input=synthesis_input, voice=voice, audio_config=audio_config
    )
    with open("final.wav", "wb") as out:
        # Write the response to the output file.
        out.write(response.audio_content)

# Converts a JSON formatted string to a normal text string
def convert_json(transcript):
    transcript = str(transcript)
    return transcript[13:len(transcript) - 3]

# Uses OpenAI Whisper API to transcribe the .wav file to text
# Implementation based off of the OpenAI documentation
# https://platform.openai.com/docs/guides/speech-to-text/quickstart
#
# Preconditions: The OpenAI API key must be set up in the environment variables
# before Whisper can be used
def transcribe(file_path):
    audio_file= open("output.wav", "rb")

    try:
        # Call the whisper API on the wav file and save the output in transcript
        transcript = openai.Audio.transcribe("whisper-1", audio_file)
        print("Transcribed Text:")
        return transcript
    except Exception as e:
        print("Error occurred during transcription: " + str(e))

    print("Done with transcribe")



# Use the pyaudio library to record audio from the user, and save it to a file
# Allow the user to start the recording with console input and stop the recording 
# by pressing the 'q' key
# Implementation of the pyaudio library based off of the pyaudio documentation
# https://people.csail.mit.edu/hubert/pyaudio/
def record_audio(stop_recording_event):
    # Global variable to indicate whether recording should occur across threads
    global record

    CHUNK = 1024 
    FORMAT = pyaudio.paInt16 
    CHANNELS = 1
    RATE = 44100 
    WAVE_OUTPUT_FILEPATH =  str(os.path.dirname(os.path.realpath(__file__))) + "\\output.wav"

    # Device specific index for the microphone, can be found by running the
    # p.get_host_api_info_by_index() function on the specific machine
    DEVICE_INDEX = 1

    p = pyaudio.PyAudio()

    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True, 
        input_device_index = DEVICE_INDEX,
        frames_per_buffer=CHUNK
    )
    frames = []
    print('Press "s" + enter to start recording, and "q" to stop recording')

    # Take the user input for start recording then start a thread to record
    # the audio_loop recording function while the main thread waits for the
    # listener to be triggered
    if 's' in input():
        record = True
        t = threading.Thread(target=audio_loop, args=(CHUNK, RATE, frames, stream, stop_recording_event))
        # The audio loop thread starts recording, seperate from the main thread
        t.start()
        print("Recording")
        with keyboard.Listener(on_press=on_press) as listener:
            # Listener thread joins back to the main thread
            listener.join()

    # Once the listener thread is triggered, stop the recording and save the
    # audio file in the current directory as a .wav file
    stop_recording_event.set()
    print("Recording Stopped")
    stream.close()
    p.terminate()
    wf = wave.open("output.wav", 'wb')
    wf.setnchannels(CHANNELS)
    wf.setsampwidth(p.get_sample_size(FORMAT))
    wf.setframerate(RATE)
    wf.writeframes(b''.join(frames))
    wf.close()

# When a key is pressed this method is called by the listener thread
def on_press(key):
    try:
        # If the key pressed is 'q' then stop the recording by changing the 
        # global variable record to false
        if key.char == 'q':
            record = False
            return False
    except AttributeError:
        pass

# The audio loop will read chunks of audio data from the microphone stream
def audio_loop(chunk, rate, frames, stream, stop_recording_event):
    while not stop_recording_event.is_set():
        # For each interval of the rate / chunk, the audio data is read from the
        # stream and appended to the frames list
        for i in range(0, int(rate / chunk)):
            # If the stop recording event is set, then break out of the loop and
            # stop the recording
            if stop_recording_event.is_set():
                break
            data = stream.read(chunk)
            frames.append(data)
    
    stream.stop_stream()
    return frames

# Implementation derived from OpenAI documentation
# https://platform.openai.com/docs/guides/chat/introduction
#
# Preconditions: The OpenAI API key must be set up in the environment variables
# before chatGPT can be used
def generate_response(message):
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=[
            {"role": "user", "content": message}
        ]
    )

    # Filter the JSON response for exclusively the response text
    return response['choices'][0]['message']['content']

if __name__ == '__main__':
    main()