from tkinter import *
from better_profanity import profanity
import text2emotion as te
import azure.cognitiveservices.speech as speechsdk
import customtkinter,time,openai,pytchat,AUTH_KEY,asyncio,pyvts,random,threading

#Configuration
ChatgptModel = 'gpt-3.5-turbo'
pitch = "+20Hz"
tts_model = "en-US-JaneNeural"
openai.api_key = AUTH_KEY.OPENAI_KEY
AzureApiKey = AUTH_KEY.AZURE_KEY
plugin_info = {
    "plugin_name": "GPT Vtube",
    "developer": "LuPow",
    "authentication_token_path": "./token.txt"
}
dead_time = 30

#SETUP VARIABLE
global ReadingChat
global myvts
ReadingChat = True
Filter = True
myvts = pyvts.vts(plugin_info=plugin_info)

#Azure TTS config
speech_config = speechsdk.SpeechConfig(subscription=AzureApiKey, region="southeastasia")
audio_config = speechsdk.audio.AudioOutputConfig(use_default_speaker=True)
speech_synthesizer = speechsdk.SpeechSynthesizer(speech_config=speech_config,audio_config=audio_config)

#Tkinter configuration
customtkinter.set_appearance_mode("System")
customtkinter.set_default_color_theme("blue")

#Random Function that make my life feel easier
def ToggleReadingChat():
    global ReadingChat
    if ReadingChat == True:
        ReadingChat = False
    elif ReadingChat == False:
        ReadingChat = True
    print(ReadingChat)

def ToggleFilter():
    global Filter
    if Filter == True:
        Filter = False
    elif Filter == False:
        Filter = True
    print(Filter)

def appendTextFile(filename,input):
    with open(filename,"a", encoding='utf-8') as f:
        f.write(input)
        f.close()

def readTextFile(filename):
    with open(filename,"r", encoding='utf-8') as f:
        read = f.read()
        f.close()
        return read

def clearTextFile(filename):
    with open(filename,"w", encoding='utf-8') as f:
        f.write("")
        f.close()

def overwirteTextFile(filename,text):
    with open(filename,"w", encoding='utf-8') as f:
        f.write(text)
        f.close()
def ClearPreviousConversationLog():

    clearTextFile("assets/Conversation_saver.txt")
    print("clear conversation file already!")

#Function that make this program work like magic
#Pick up Random topic to talk about
def RandomTopic():
    with open("assets/RandomTopic.txt", 'rb') as file:
        lines = file.readlines()
        random_line = random.choice(lines).decode('cp874')
    speakEN(random_line.strip())
    threading.Thread(appendTextFile("assets/Conversation_saver.txt",f"\nLuana-chan:{random_line.strip()}")).start()

#speak using Azure TTS and detect emotion of text(I hate nltk)
def speakEN(text):
    #get emotion from text
    emotion_dict = te.get_emotion(text)
    #find the most emotion score
    max_emotion = max(emotion_dict, key=emotion_dict.get)

    #defind emotion for SSML azure TTS
    if "whisper" in text or "whispering" in text:
        emotion = "Whispering"
    elif "shouting" in text or "shout" in text or "yell" in text or "SHOUT" in text or "YELL" in text:
        emotion = "Shouting"
    elif max_emotion == "Happy":
        #asyncio.run(trigger(3))
        emotion = "Cheerful"
    elif max_emotion == "Angry":
        #asyncio.run(trigger(4))
        emotion = "Angry"
    elif max_emotion == "Sad":
        #asyncio.run(trigger(5))
        emotion = "Sad"
    else:
        #asyncio.run(trigger(3))
        emotion = "Default"

    #Set SSML text for using to configuration voice
    ssml_string = f'<speak version="1.0" xmlns="https://www.w3.org/2001/10/synthesis" xml:lang="en-US"><voice name="{tts_model}" style="{emotion}"><prosody pitch="{pitch}">{text}</prosody></voice></speak>'
    result = speech_synthesizer.speak_ssml_async(ssml_string).get()

#Get responsed from openAI
def GPTResponsed(text):
    #Get response by attach personality and old conversation and prompt that user give
    response = openai.ChatCompletion.create(
    model=ChatgptModel,
    messages=[
        {"role": "system", "content": readTextFile("assets/Preprompt.txt") + readTextFile("assets/TrainModel.txt") + readTextFile("assets/Conversation_saver.txt")},
        {"role": "user", "content": text}
    ],
    temperature=.7,
    top_p=1,
    frequency_penalty=0.12,
    presence_penalty=0.2
    )     
    #print reply and how much token spend to console
    print(f'Reply:{response.choices[0].message.content}')
    print(f'*Succes Generate response token spend: {response.usage.total_tokens}')

    #return responed
    return response.choices[0].message.content

#connect to VtubeStudio to use api
async def connect_auth():
    global hotkey_list
    await myvts.connect()
    await myvts.request_authenticate_token()
    await myvts.request_authenticate()
    response_data = await myvts.request(myvts.vts_request.requestHotKeyList())
    hotkey_list = []
    for hotkey in response_data["data"]["availableHotkeys"]:
        hotkey_list.append(hotkey["name"])
    await myvts.close()

#trigger Hotkey on VtubeStudio
async def trigger(choice):
    await myvts.connect()
    await myvts.request_authenticate()
    send_hotkey_request = myvts.vts_request.requestTriggerHotKey(hotkey_list[choice])
    await myvts.request(send_hotkey_request)  # send request to play 'My Animation 1'
    await myvts.close()

#Help 
def run():
    try:
        global chat
        global ChatLabel
        global Responsed
        stream_ID = StreamIDInput.get()
        chat = pytchat.create(video_id=stream_ID)
        print("*Chat is connected!")

        #Set up display label
        Responsed = customtkinter.CTkLabel(master=Innerframe,text="Responsed",font=("Roboto",28),wraplength=1200)
        Responsed.pack()
        ChatLabel = customtkinter.CTkLabel(master=Innerframe,text="Message",font=("Roboto",20),wraplength=1000)
        ChatLabel.pack(pady=10)
        RunButton.configure(state="disabled")
        RunButton.configure(text="Running")
        StreamIDInputField.configure(state="disabled")
        StreamIDInputField.configure(show = "*")

        Innerframe.pack(pady=20,padx=20, fill="both",expand=True)
        threading.Thread(target=ChatConnected).start()
    except Exception as e:
        print(f"Error detect! Error Info:{e}")
    

def ChatConnected():
    start_time = time.time()
    while True:
        if time.time() - start_time >= dead_time:
            print("Call random Topic")
            RandomTopic()
            start_time = time.time()
        else:
            if chat.is_alive():
                for c in chat.get().sync_items(): 
                    start_time = time.time()        
                    message = f'{c.author.name}:{c.message}'
                    print(message)
                    if ReadingChat:
                        if Filter and profanity.contains_profanity(message): 
                            print("*Filter*")
                        else:
                            reply = GPTResponsed(message)
                            # asyncio.run(startvts())       
                            threading.Thread(speakEN(reply.replace("Luana-chan:", ""))).start()
                            threading.Thread(Responsed.configure(text=reply)).start()
                            threading.Thread(ChatLabel.configure(text=message)).start()
                            threading.Thread(appendTextFile("assets/Conversation_saver.txt",f"\n{message}")).start()
                            threading.Thread(appendTextFile("assets/Conversation_saver.txt",f"\n{reply}")).start()
                        #asyncio.run(trigger(6))
                        start_time = time.time() 
                #else:
                    #asyncio.run(trigger(random.randint(0, 2)))
                    #time.sleep(random.randint(0,3)) 

asyncio.run(connect_auth())
root = customtkinter.CTk()
root.title("GPT Vtube")
width= root.winfo_screenwidth()               
height= root.winfo_screenheight()               
root.geometry("%dx%d" % (width, height))

frame = customtkinter.CTkFrame(master=root)
frame.pack(pady=20,padx=60, fill="both",expand=True)


Title = customtkinter.CTkLabel(master=frame,text="GPT Vtube Luncher",font=("Roboto",24)).pack()

StreamIdLabel = customtkinter.CTkLabel(master=frame,text="Youtube Stream ID",font=("Roboto",16)).pack(pady=2)

StreamIDInput = StringVar()
StreamIDInputField = customtkinter.CTkEntry(master=frame,textvariable=StreamIDInput,width=500,height=30)
StreamIDInputField.pack(padx=10)

RunButton = customtkinter.CTkButton(master=frame,text="Run",font=("Roboto",16),command=run)
RunButton.pack(pady=5)

ClearConversationLog = customtkinter.CTkButton(master=frame,text="Clear Conversation",font=("Roboto",16),command=ClearPreviousConversationLog)
ClearConversationLog.pack(pady=2)
switchReadingChat = customtkinter.CTkSwitch(master=frame, text="Reading Chat",command=ToggleReadingChat)    
switchReadingChat.select()
switchReadingChat.pack()

switchFilter = customtkinter.CTkSwitch(master=frame, text="Filter Bad Words",command=ToggleFilter)    
switchFilter.select()
switchFilter.pack()

Innerframe = customtkinter.CTkFrame(master=frame)

root.mainloop()

print("closed program")