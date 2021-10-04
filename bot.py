#IN THE NAME OF ALLAH (GOD)

from flask import Flask, request
from gapbot import Gap
import json,time,pytz,threading,os
import jdatetime #JALALI (SHAMSI) calender
from gapbot.client import gap
from datetime import datetime
from sqlalchemy import create_engine
import values as var

#this app work 18 hours a day because run on free heroku account!
#avoid getting sleep with http://kaffeine.herokuapp.com/ (just set start time of sleep)
bot = Gap(bot_token = var.gap_bot_token)
app = Flask(__name__)

#SQL
#to init table of sql , run sqlInit.py with command
DATABASE_URL = os.environ['DATABASE_URL']
if DATABASE_URL.startswith("postgres://"):
    DATABASE_URL = DATABASE_URL.replace("postgres://", "postgresql://", 1)
d = create_engine(DATABASE_URL, echo = False)

firstmsgkey=var.msgContent

def convertToJalali(time_str_Or_datetime,jalali_format=var.jalaliFormat):
    '''
    get gregorian and convert to jalali (shamsi)
    this function can detect type of variable (datetime or str) 
    and finally return str jalali
    '''
    jdatetime.set_locale('fa_IR')

    if   type(time_str_Or_datetime) is datetime :
        strJalali=jdatetime.datetime.fromgregorian(datetime=time_str_Or_datetime).strftime(jalali_format)
        return strJalali

    elif type(time_str_Or_datetime) is str :
        gregorian=datetime.strptime(time_str_Or_datetime,var.timeformat) #str to time
        strJalali=jdatetime.datetime.fromgregorian(datetime=gregorian).strftime(jalali_format)
        return strJalali

def fullKeyBoard(ownerMsg):
    '''
    return keyboard contain 
    -return bottom
    -schedule (timed) bottom
    -support bottom
    -setting bottom
    -guide bottom
    -donate bottom
    -list of all timed msg with date of send and which ID must sent
    like this ->(channelName | چهارشنبه19خرداد 06:00)
    '''
    mainKeyborad={
        "keyboard": [
            [
                {"برگشت": "🔙برگشت"},
                {"پیام زمان‌دار": "پیام زمان‌دار⏲"}
            ],
            [
               {"پشتیبانی":"💬پشتیبانی"},
               {"تنظیمات":"تنظیمات⚙️"},
               {"حمایت":"⛽️حمایت"},
               {"راهنما":"راهنما❕"}
            ]
        ],}
    finall =mainKeyborad
    qrryy="SELECT time,num,message from messagelists WHERE userid='"+str(ownerMsg)+"' ORDER BY num"
    for timerow in d.execute(qrryy):
        #get channel name from message data for show in keyboard
        #timerow[2]={'chat_id': '@jookelandd', 'data' ...
        chName=str(timerow[2]).split("'@")[1]
        chName=chName.split("'")[0]

        #convert gregorian to jalali ,timerow[0]="2021:06:09 06:00"
        textKey=convertToJalali(str(timerow[0]),"%a%d%b %H:%M") +' | '+ chName
        #textKey=channelName | چهارشنبه19خرداد 06:00
        
        valuekey=firstmsgkey+str(timerow[1])+'u81'+str(ownerMsg)
        #valuekey=(blanck emoji)+row+sqlnum+u81+userid
        rowKeyMsg = [{ valuekey : textKey }]
        finall["keyboard"].append(rowKeyMsg)
    return finall

def currentTehranTime():
    #get current tehram time
    tehran = pytz.timezone("Asia/Tehran")
    datatime_ist=datetime.now(tehran)
    time=datatime_ist.strftime(var.timeformat)
    return time

def sendSchedulePostfromSql():
    #this func always running by sendMsgThread , to send msg that time reach to send
    while 1:
        now=currentTehranTime()
        print("thread ",now)
        
        qrc="SELECT time,message,userid,token from messagelists ORDER BY num"
        for row in d.execute(qrc):
            timeMsg   =str (row[0])
            msgDetail =eval(row[1]) #convert str to dict for sending
            ownerMsg  =str (row[2])
            tokenUser =str (row[3])

            if now >= timeMsg :
                #send it with token of user to him/her channels ,
                #  send resualt to user , delete row
                userBot = Gap(bot_token = tokenUser)
                ress = userBot._send(method='sendMessage',data=msgDetail)
                timeMsg=convertToJalali(timeMsg) #gregorian str to jalali str

                if ress.status_code == 200 :
                    caption="پست با زمان\n"+timeMsg+"\nبا موفقیت ارسال شد !"
                    logtome("➡️➡️📨\nmsgTime:"+timeMsg+"\nmsgSend:"+convertToJalali(now))
                else :
                    logtome("➡️➡️📨❌1 error\n"+str(row)+"\n\n"+str(ress))

                    #try to send again
                    ress = userBot._send(method='sendMessage',data=msgDetail)
                    if ress.status_code == 200:
                        caption="پست با زمان\n"+timeMsg+"\nبا موفقیت ارسال شد !"
                        logtome("➡️➡️📨\nmsgTime:"+timeMsg+"msgSend:"+convertToJalali(now))
                    else:
                        logtome("➡️➡️📨❌2 error\n"+str(row)+"\n\n"+str(ress))
                        caption="پست با زمان\n"+timeMsg+"متاسفانه ارسال نشد! با پشتیبانی ارتباط برقرار کنید" 

                
                #to avoid show this msg in keyborad.first remove row then report to user
                qrry="DELETE FROM messagelists WHERE message=(%s)"
                d.execute(qrry,[str(msgDetail)])

                bot.send_text(ownerMsg,caption,reply_keyboard = fullKeyBoard(ownerMsg))                    
            
        time.sleep(60)

def logtome(text):
    #send text to my gap account or my test channel
    try:
        bot.send_text(var.IDReport,str(text))
    except:
        pass
def gettingTokenID(formdata):
    #getting channel id and token from form data
    formdata=formdata.split("chanNel=")[1] # $#@channel=
    formdata=formdata.split("&TokEn=")#return list with channelID and Token
    userChannelID='@'+formdata[0] #aiaiai
    userToken=formdata[1]     #4543545345
    return [userChannelID,userToken]

def giveFormTimeSend(whoSendmeMsg):
    '''
    this func get list of channel that user has them,put it in form and ask for 
    -Channel (with checkbox)
    -hours
    -minetes
    '''
    #get all list of channel id to show in checkbox of form
    qqrrryy = "SELECT channelid from userdata where chatid="+whoSendmeMsg
    row = d.execute(qqrrryy).fetchone()
    row = row[0].split("/")
    listID=[]
    for k in row:
        IDSelect={k:k}
        listID.append(IDSelect)

    formTimeSend=[
            {"name": "ID", "type": "select", "label": "ارسال پیام به ایدی(کانال/گروه)", "options": listID},
            {"name": "DaYs", "type": "select", "label": "?برای چه روزی ارسال بشه","options": var.listDays},
            {"name": "hours", "type": "text", "label": "ساعت"},
            {"name": "mintues", "type": "text", "label": "دقیقه"},
            {"type": "submit", "label": "ok"}
            ]
    
    return formTimeSend

sendMsgThread = threading.Thread(target=sendSchedulePostfromSql)

'''                
status:  (in sql column)
getToken = if user want change token or channel
waitToGetTime = user click on پیام زماندار and send form to it.wait to get time
readytogo = user set time and now bot ready to get msg to send all to his channel in future
noneNull== defualt and usuall status (nothing do anything)
msgDelOrNot = wait to user deside remove msgSchedule or no
getNewID=if user want add new ID of his/her channel or group
DelID = if user want to delete one of their id s
'''
'''
this bot has 2 table for it database
userdata = save channels ids ,last time for sending post,token,last id select for send post to it
messagelists= save msg content that must be send for special date to special channel
'''
@app.route('/', methods=['POST'])
def answer():
    '''
       Someone send me a message ,Is he/she register in my db?

       NO - send form to it and register it.
       YES- send keyboard , present service
    '''
    message = request.form.to_dict(flat=False)
    logtome(str(message))
    #message={'chat_id': ['13614'], 'data': ['dfgdfg'], 'from': ['{"id":1998,"name":"mahdi","user":"mahdiAI313"}'], 'type': ['text']} 
    whoSendmeMsg=str(message['chat_id'][0])

    #Is user register in my db (existed in my sql)?
    qryyy="SELECT status,timesendpost,idselected,token,channelid from userdata where chatid="+whoSendmeMsg
    resualt=d.execute(qryyy).fetchone()
    if resualt == [] : resualt = None;
    
    #1-user not existed in sql
    if   resualt == None and message['type'] != ['submitForm']:
        #send Guid and form to register in my bot
        bot.send_text(whoSendmeMsg,var.GuidCaption,reply_form=var.formSetting)
        return '200'
    elif resualt == None  and message['type'] == ['submitForm']:
        '''get Form from user ,let's register user!
        -delete form 
        -getting channel id and token from form data
        -send msg to channel to test channelID and Token
        -add user data to sql
        '''
        message=json.loads(message['data'][0]) # str to json{}
        ss=bot.delete_message(whoSendmeMsg,message['message_id']) #delete Form
        # logtome("msg delete with "+str(ss))
        #message['data'][0]  =  "chanNel:@aiaiai&TokEn:4543545345"
    
        userChannelID,userToken = gettingTokenID(message['data'])

        #check if token or channelID isnt correct!
        userBot=Gap( bot_token = userToken )
        res=userBot.send_text( userChannelID , '.')

        if res.status_code != 200 :
            #user enter incorrect data, send guid and Form again
            bot.send_text(
                    whoSendmeMsg,
                    var.incorrectFormCaption,
                    reply_form=var.formSetting)
            return '400'
        else:
            #user enter correct data , lets added user to sql
            qryyy="INSERT INTO userdata (status,chatid,channelid,token) VALUES (%s,%s,%s,%s);"
            d.execute( qryyy , ["noneNull",whoSendmeMsg,userChannelID,userToken ])
            bot.send_text(
                whoSendmeMsg,
                var.wellcomeCaption,
                reply_keyboard=fullKeyBoard(whoSendmeMsg)
            )
            return '200'

    #2-user existed in sql 
    userStatusSql    = str( resualt[0] ) 
    userLastTimeSql  = str( resualt[1] )
    userIDselectedsql= str( resualt[2] ) #must contain @ for channel
    userTokenSql     = str( resualt[3] )
    userChannelsIDs  = str( resualt[4] )
    
    #attention!!! : dont cahnge order of these if conditions otherwise got bug !!
    # tartib if hay zir mohem hastan! moragheb bash vagarna be bug mikhori :| !
    if   resualt != None and message['data'] == ['پیام زمان‌دار'] :
        formTimeSend=giveFormTimeSend(whoSendmeMsg)

        bot.send_text(
            whoSendmeMsg,
            var.newMsgcaption,
            reply_form=formTimeSend,
            reply_keyboard = var.backKeyboard)

        qryy="UPDATE userdata set status='waitToGetTime' where chatid="+whoSendmeMsg
        d.execute(qryy)
    elif resualt != None and message['data'] == ['برگشت']  :
        bot.send_text(
            whoSendmeMsg,
            var.backKeyCaption ,
            reply_keyboard = fullKeyBoard(whoSendmeMsg)
            )

        qryy="UPDATE userdata set status='noneNull' where chatid="+whoSendmeMsg
        d.execute(qryy)
    elif resualt != None and message['data'] == ['تنظیمات'] :
        bot.send_text(
            whoSendmeMsg,
            var.emptyEmoji,
            reply_keyboard = var.settingKeyboard
        )
    elif resualt != None and message['data'] == ['تغییر توکن'] :
        bot.send_text(
            whoSendmeMsg,
            var.changeToken,
            reply_form=var.formSetting,
            reply_keyboard = var.backKeyboard
        )
        qryy="UPDATE userdata set status='getToken' where chatid="+whoSendmeMsg
        d.execute(qryy)
    elif resualt != None and message['data'] == ['افزودن ایدی'] :
        bot.send_text(
            whoSendmeMsg,
            var.addNewID,
            reply_form=var.formNewID,
            reply_keyboard = var.backKeyboard
        )
        qryy="UPDATE userdata set status='getNewID' where chatid="+whoSendmeMsg
        d.execute(qryy)
    elif resualt != None and message['data'] == ['حذف ایدی'] :
        formDelete=giveFormTimeSend(whoSendmeMsg)
        #we need just first checkbox to select channel id and a button of send
        for i in range(0,len(formDelete)-2) :
            formDelete.pop(1)
        formDelete[1]['label']='پاکش کن'

        bot.send_text(
            whoSendmeMsg,
            var.removeID,
            reply_form=formDelete,
            reply_keyboard = var.backKeyboard
        )
        qryy="UPDATE userdata set status='DelID' where chatid="+whoSendmeMsg
        d.execute(qryy)
    elif resualt != None and message['data'] == ['پشتیبانی'] :
        bot.send_text(
            whoSendmeMsg,
            var.supportCaption,
            reply_keyboard = fullKeyBoard(whoSendmeMsg)
            )
    elif resualt != None and message['data'] == ['حمایت'] :
        bot.send_text(
            whoSendmeMsg,
            var.donateCaption,
            reply_keyboard = fullKeyBoard(whoSendmeMsg)
            )
    elif resualt != None and message['data'] == ['راهنما'] :
        bot.send_text(
            whoSendmeMsg,
            var.GuidCaption,
            reply_keyboard = fullKeyBoard(whoSendmeMsg)
            )
    elif userStatusSql == 'getNewID' and message['type'] == ['submitForm'] :
        #change setting of user channel or group ID
        '''
        -delete form
        -send msg to newID for test
        -if test=True , add newID to sql
        '''
        message = json.loads(message['data'][0])              #str to json{}
        bot.delete_message(whoSendmeMsg,message['message_id'])#delete Form

        newID = '@'+message['data'].split("chanNel=")[1]

        qyyr="SELECT token,channelid from userdata where chatid=%s"
        userToken,lastID = d.execute(qyyr,[whoSendmeMsg]).fetchone()
        # userToken = str(row[0])
        # lastID    = str(row[1])

        userBot=Gap( bot_token = userToken )
        res=userBot.send_text( newID , '.')
        if res.status_code != 200 :
            #user enter incorrect data, send guid and Form again
            bot.send_text(
                    whoSendmeMsg,
                    var.incorrectNewID,
                    reply_form=var.formNewID,
                    reply_keyboard = var.backKeyboard
                    )
        else:
            #user enter correct data , lets update user to sql
            qryyy="UPDATE userdata SET status='noneNull',channelid=%s WHERE chatid="+whoSendmeMsg
            d.execute( qryyy,[str(lastID+'/'+newID)])
            bot.send_text(
                whoSendmeMsg,
                var.updateSettingCap,
                reply_keyboard=fullKeyBoard(whoSendmeMsg)
            )
    elif userStatusSql == 'getToken' and message['type'] == ['submitForm'] :
        #change setting of user token
        '''
        -delete form
        -send msg to ID with inserted token
        -if test=True , change token in sql
        '''
        message = json.loads(message['data'][0])              #str to json{}
        sss=bot.delete_message(whoSendmeMsg,message['message_id'])#delete Form
        # logtome("msg delete with "+str(sss))
        
        userChannelID,userToken = gettingTokenID(message['data'])
        #check if token or channelID isnt correct!
        userBot=Gap( bot_token = userToken )
        res=userBot.send_text( userChannelID , '.')
        if res.status_code != 200 :
            #user enter incorrect data, send guid and Form again
            bot.send_text(
                    whoSendmeMsg,
                    var.incorrectFormCaption,
                    reply_form=var.formSetting)
            return '200'
        else:
            #user enter correct data , lets update user to sql
            qryyy="UPDATE userdata SET token=%s WHERE chatid="+whoSendmeMsg
            d.execute( qryyy,[userToken])
            bot.send_text(
                whoSendmeMsg,
                var.updateSettingCap,
                reply_keyboard=fullKeyBoard(whoSendmeMsg)
            )
    elif userStatusSql == 'DelID' and message['type'] == ['submitForm'] :
        ''' we recive form conatian one of user ID
        -delete Form
        -get list of all id of user
        -remove recive id from list of IDs
        -set status to noneNULL
        '''
        # message="{'chat_id': ['1'], 'data': ['{"callback_id":"11","data":"ID=%40bshshsh","message_id":388}\n'], 'type': ['submitForm']}
        msgJson=json.loads(message['data'][0])
        sss=bot.delete_message(whoSendmeMsg,msgJson['message_id'])
        # logtome("msg delete with "+str(sss))
        
        #checking. if user has 1 id , cant remove it. first add new id then came and remove last id
        if userChannelsIDs.find("/") == -1 :
            bot.send_text(
                whoSendmeMsg,
                var.cantRemoveID,
                reply_keyboard = fullKeyBoard(whoSendmeMsg))
            return '400'

        # -remove recive id from list of IDs
        ids = userChannelsIDs #like "@mm/@ff/@ss/@sss"

        t1=msgJson['data'].replace('%40','@')#"%40ss" -> @ss
        selectIDforRemove = t1.replace('ID=','')

        ids = ids.split("/")
        listID=[]
        for k in ids:
            listID.append(k) #['@mm','@ff','@ss','@sss]
        addresIDSelected=listID.index(selectIDforRemove)
        listID.pop(addresIDSelected) 

        #listId to str  then to sql
        li=str(listID)   #['@mm', '@ff', '@ss', '@sss']
        li=li.replace(']','')
        li=li.replace('[','')
        li=li.replace("'",'')
        li=li.replace(',','/')
        li=li.replace(' ','') #@mm/@ff/@ss/@sss

        qryy="UPDATE userdata set channelid=%s where chatid="+whoSendmeMsg
        d.execute(qryy,[li])

        bot.send_text(
            whoSendmeMsg,
            var.updateSettingCap,
            reply_keyboard = fullKeyBoard(whoSendmeMsg))
    elif userStatusSql == 'waitToGetTime' and message['type'] == ['submitForm'] :
        
        '''now we recive Form that contain Time and ID(group/Channel) for send msg
        -delete Form
        -check value input 
        -send msg to say we ready to get your msg
        -set status=readytogo
        '''
        #old message={'chat_id': ['xxxx'], 'data': ['{"callback_id":"xxxx","data":"hours=22&mintues=00","identifier":"xxxx","message_id":1904}\n']...
        #--> message['data'][0] = 1904
        #new msg contain ID=@channel
        data=json.loads(message['data'][0])
        sss=bot.delete_message(whoSendmeMsg,data['message_id'])
        # logtome("msg delete with "+str(sss))

        tp=str(data['data']) #DaYs=0&ID=@bshsh&hours=12&mintues=45
        tp=tp.replace("ID=",'')
        IDselect=tp.split("&")[0] #ID of channel or group we must send msg to it
        tp=tp.replace(IDselect+'&','')
        IDselect=IDselect.replace("%40",'@') #maybe instead of @  , gap send us %40
        tp=tp.replace("DaYs=",'')
        DaYs=int(tp[0])
        tp=tp[2:] #remove 0&  ->  tp=hours=14&mintues=16&Delete=7
        tp=tp.replace("hours=",'')
        tp=tp.replace("&",':')
        tp=tp.replace("mintues=",'')

        #check if input time isnt correct
        try:
            msgtime=datetime.strptime(tp,'%H:%M')#convert str to time to work easier
        except:
            bot.send_text(
                whoSendmeMsg,
                var.errorTime+var.newMsgcaption,
                reply_form = giveFormTimeSend(whoSendmeMsg),
                reply_keyboard = var.backKeyboard)
            return '400' #never delete this line, because user input incorrect time.must pause code

        IST = pytz.timezone("Asia/Tehran")
        now=datetime.now(IST)
        msgdatetime=now.replace(day=now.day+DaYs,hour=msgtime.hour, minute=msgtime.minute)#convert to like 2021:05:23 12:34
        # logtome(msgdatetime)

        #if time that user input is for next day
        if msgdatetime < now :
            #exam: now=22:30  tp=6:30 so tp is next day
            msgdatetime=msgdatetime.replace(day=msgdatetime.day+1)

        #for show better for iraninan user convert to jalali. msgJalali=چهارشنبه 19 خرداد 1400 06:00
        msgJalali=convertToJalali(msgdatetime)
        caption=" برای زمان "+str(msgJalali)+"\n و ایدی "+IDselect+"تنظیم شد."+var.readytogetmsg
        bot.send_text(whoSendmeMsg,caption,reply_keyboard = var.backKeyboard)

        msgdatetime=msgdatetime.strftime(var.timeformat) # time (datetime) to str

        qry="UPDATE userdata set status='readytogo',idselected=%s,timesendpost=%s where chatid="+whoSendmeMsg
        d.execute(qry,[IDselect,msgdatetime])
    elif userStatusSql != 'msgDelOrNot' and message['data'][0].startswith(firstmsgkey):
        '''
        show timed message before sending to see it or delete it !
        -decrept content of data that recieve
        -send thier timed message to user
        -send keyboard to decide return or delete it.
        '''
        #data recive like this -> '\u200drow209u81136490514'
        #contain empytyemoji+row+sqlnum+u81+owenerid
        
        #clear data to "sql numeber of msg"  and  "userid of owner of msg"
        t1=message['data'][0].split(firstmsgkey)[1] #'209u81136490514'
        t1=t1.split("u81") # t1[0]=209   t1[1]=136490514
        msgNum=t1[0]
        owenerId=t1[1]

        #show msg to user(owner)
        qqrryy="SELECT message,time from messagelists where userid=%s AND num=%s"
        rowMsgsql = d.execute(qqrryy,[owenerId,msgNum]).fetchone()
        msgScheduleContent = eval(rowMsgsql[0]) #str to dict
        timeSchedulePost = rowMsgsql[1]#2021:08:16 13:13  
        msgScheduleContent['chat_id'] = [whoSendmeMsg]
        res=bot._send(method='sendMessage',data=msgScheduleContent)

        timeSchedulePost=convertToJalali(timeSchedulePost)

        #send keyboard to deside remove or not  and set status=msgDelOrNot 
        qry="UPDATE userdata set status='msgDelOrNot' where chatid="+whoSendmeMsg
        d.execute(qry)

        delMsgKeyboard={
            "keyboard": [
            [
                {"برگشت": "برگشت"},
                {message['data'][0]:var.textKeyRemove}
            ]
            ],}
        caption=var.capScheduletimePost+timeSchedulePost+"☝☝" #⏰ زمان ارسال:18:00
        bot.send_text(whoSendmeMsg,caption,reply_keyboard =delMsgKeyboard)
    elif userStatusSql == 'msgDelOrNot' and message['data'][0].startswith(firstmsgkey):
        #user want to delete msg from our sql to avoid send!

        #data recive like this -> '\u200drow209u81136490514'
        #contain empytyemoji+row+sqlnum+u81+owenerid
        #clear data to "sql numeber of msg"  and  "userid of owner of msg"
        t1=message['data'][0].split(firstmsgkey)[1] #'209u81136490514'
        t1=t1.split("u81") # t1[0]=209   t1[1]=136490514
        msgNum=t1[0]
        owenerId=t1[1]

        qrrry="DELETE FROM messagelists WHERE num=%s and userid=%s"
        d.execute(qrrry,[msgNum,owenerId])

        bot.send_text(whoSendmeMsg,var.msgRemove,reply_keyboard=fullKeyBoard(whoSendmeMsg))
        qry="UPDATE userdata set status='noneNull' where chatid="+whoSendmeMsg
        d.execute(qry)
    elif userStatusSql == 'readytogo' :
        '''
        user select time for thier msg , and any msg that recive ,we must put it in our sql
        '''
        message['chat_id'] = userIDselectedsql
 
        qryyy="INSERT INTO messagelists (time,message,userid,token) VALUES (%s,%s,%s,%s);"
        val=(userLastTimeSql,str(message),whoSendmeMsg,userTokenSql)
        d.execute(qryyy,val)
        #sendMsgThread is always running , and see new change in sql , 
        # it will send this message,dont worry
        bot.send_text(whoSendmeMsg,var.emptyEmoji,reply_keyboard = fullKeyBoard(whoSendmeMsg))
    else:
        #incorrect enterance from user.
        bot.send_text(
            whoSendmeMsg,
            var.unknownStatus ,
            reply_keyboard = fullKeyBoard(whoSendmeMsg)
            )
        qryy="UPDATE userdata set status='noneNull' where chatid="+whoSendmeMsg
        d.execute(qryy)
    return '200'

@app.route('/', methods=['GET'])
def wakeThreadUP():
    '''
        this func get thread alive to send timed(schedule) message at correct time to channel!
        heroku goes off after 30min and http://kaffeine.herokuapp.com/#decaf
        send msg to us to avoid sleeping.
    '''
    try:
        if sendMsgThread.is_alive() == False :
            print("start wakeThreadUP from GET")
            sendMsgThread.start()
    except:
        logtome("➡️➡️📨\ncant start Thread")
    return '200'

#after set code to heroku or update code,this line cause thread start.
wakeThreadUP()

if __name__ == '__main__':
    app.run(threaded=True)

