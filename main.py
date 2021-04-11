import discord, sqlite3, datetime, asyncio, time
from discord.ext import tasks, commands
from discord.utils import get

#совершается подключение к базе данных
conn = sqlite3.connect('database.db', detect_types=sqlite3.PARSE_DECLTYPES|sqlite3.PARSE_COLNAMES)
cursor = conn.cursor()

#здесь какая-то нужная фигня для дискорда
intents = discord.Intents.default()
intents.members = True
client = discord.Client(intents=intents)

#список ботов чтобы не искать их снова и снова
botlist = []
activeVote = False

#специальный ембед с помощью
embedHelp = discord.Embed(title="Вот всё, что ты можешь на данный момент:", description="", color=0x00ff00)
embedHelp.add_field(name=".credit (s)", value="показывает твой социальный рейтинг и ранг (в подарок картинка!)", inline=False)
embedHelp.add_field(name=".vote <юзер> <+/-количество_баллов>", value="вот тут происходит настоящая демократия в священной компартии Китая! Этой командой можно решать судьбы!", inline=False)
embedHelp.add_field(name="Что можно делать с командой .vote?", value="голосовать за других; раз в день; максимум 30 или 25 баллов", inline=False)
embedHelp.add_field(name="Что нельзя делать с командой .vote?", value="голосовать за себя; больше раза в день; больше этого лимита", inline=False)

@client.event
async def on_ready():
    print("|----------------------------------|")
    print("|Rzx's Social Credit Bot (beta 0.1)|")
    print("|----------------------------------|")
    print("\n\nБот работает на этих серверах:\n")
    for guild in client.guilds:
        print(guild.name)
        for member in guild.members:
            if member.bot:
                botlist.append(member.id)
            else:
                #проверяю, появлялись ли новые люди пока бот не работал
                cursor.execute(f"""SELECT id FROM users WHERE id={member.id}""")
                if cursor.fetchone() == None:
                    print("Найден пользователь без рейтинга: ",member.name,end="")
                    cursor.execute(f"""INSERT INTO users ("id", "name", "score", "voted") VALUES ({member.id}, "{member}", 1000, 0)""")
                    print(" || Значения добавлены!",end="\n")
                else:
                    pass
                #проверяю, актуальные ли данные голосований у всех
                date = datetime.date.today()
                sqlDate = datetime.datetime.now().strftime("%Y-%m-%d")
                cursor.execute(f"""SELECT lastvotedate FROM users WHERE id={member.id}""")
                voteDateStats = cursor.fetchone()
                if voteDateStats[0] == None:
                    #запаковываю нужную информацию в кортеж
                    data = (sqlDate,member.id)
                    print(datetime.datetime.now(),' |',member.name,'| не найдена дата последнего голосования')
                    cursor.execute("""UPDATE users SET lastvotedate=? WHERE id=?""",data)
                elif voteDateStats[0] < date:
                    data = (sqlDate,member.id)
                    print(datetime.datetime.now(),' |',member.name,'| добавлено ежедневное право голосовать')
                    cursor.execute(f"""UPDATE users SET voted={0} WHERE id={member.id}""")
                    cursor.execute("""UPDATE users SET lastvotedate=? WHERE id=?""",data)
                else:
                    print(datetime.datetime.now(),' | вся информация актуальная')
                #сохраняем
                conn.commit()
    print("\n",datetime.datetime.now()," | Всё готово!",end="\n------------------------------------------\n")
    print("\nСписок ботов на серверах: \n",botlist)

@client.event
async def on_member_join(member):
    print("Появился новый пользователь на сервере ",member.guild.name)
    cursor.execute(f"""SELECT id FROM users WHERE id={member.id}""")
    if member.bot:
        botlist.append(member.id)
        print("Неважно, это бот :с")
    else:
        if cursor.fetchone() == None:
            print("Пользователь без рейтинга: ",member.name,end="")
            cursor.execute(f"""INSERT INTO users ("id", "name", "score", "voted") VALUES ({member.id}, "{member}", 1000, 0)""")
            sqlDate = datetime.datetime.now().strftime("%Y-%m-%d")
            data = (sqlDate,member.id)
            cursor.execute("""UPDATE users SET lastvotedate=? WHERE id=?""",data)
            print(" || Значения добавлены!")
        else:
            pass
    conn.commit()

#в этот кортеж вписаны варианты написания команды .credits
creditCommand = (".credit", ".credits")
#а в этом кортеже варианты написания .vote
voteCommand = (".vote")
#а в вот этот кортеж вписаны варианты написания команды .help
helpCommand = (".help", ".info")

#основная функция бота здесь: принимает сообщения и решает что ему дальше делать
#тут функции .credit
@client.event
async def on_message(message):
    #бот ограничен в правах :c
    if message.author == client.user:
        return
    if message.content.startswith("."):
        typeOfCommand = None
        messageContent = message.content.lower()
        #определяется, что это за команда
        for i in helpCommand:
            if messageContent.startswith(i):
                typeOfCommand = "help"
                break
        if typeOfCommand == None:
            for i in creditCommand:
                if messageContent.startswith(i):
                    typeOfCommand = "credit"
                    break
        if typeOfCommand == None:
            for i in voteCommand:
                if messageContent.startswith(i):
                    typeOfCommand = "vote"
                    break
        #ложное срабатывание
        if typeOfCommand == None:
            return
        #код для команды .credit
        if typeOfCommand == "credit":
            cursor.execute(f"""SELECT score FROM users WHERE id={message.author.id}""")
            score = cursor.fetchone()
            if score != None:
                rating = findRating(score[0])
                ratingPicture = findRatingPicture(rating)
                answer = ["<@",message.author.id,"> , у тебя ",score[0]," баллов социального рейтинга!\nТвой ранг: ", rating]
                await message.channel.send("".join(map(str,answer)),embed=ratingPicture)
            else:
                answer = ["<@",message.author.id,"> , ты , похоже, не гражданин Китая!"]
                await message.channel.send("".join(map(str,answer)))
            print(datetime.datetime.now()," | ",message.author," | команда .credits выполнена.",)
        elif typeOfCommand == "vote":
            #смотрим что нет активных голосований (хотя глянем это ещё раз потом)
            if activeVote:
                answer = ["<@",message.author.id,"> , уже проходит голосование, подожди немного!"]
                await message.channel.send("".join(map(str,answer)))
                await message.delete()
                print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | голосование уже ведётся",)
            else:
                votingDetails = message.content.split()
                #проверяем, не вписали ли чего лишнего в команду
                if len(votingDetails) != 3:
                    answer = ["<@",message.author.id,"> , эта команда вводится в формате {.vote <юзер> <+/-количество_баллов>}!\nПопробуй ещё раз."]
                    await message.channel.send("".join(map(str,answer)))
                    await message.delete()
                    print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | аргументов больше чем нужно.")
                else:
                    #убираю всё лишнее из строки с id юзера
                    voteId = votingDetails[1].strip("<@!>")
                    #проверяю длину id, чтобы лишний раз не проверять неверный id
                    if len(voteId) != 18:
                        answer = ["<@",message.author.id,">, id пользователя, который ты ввёл не похож на настоящий! Ты точно делаёшь всё верно?"]
                        await message.channel.send("".join(map(str,answer)))
                        await message.delete()
                        print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | длина id не равна 18")
                    else:
                    #пробую перевести id в целое число чтобы сравнивать его дальше
                        trueId = False
                        try:
                            voteId = int(voteId)
                        except Exception as err:
                            answer = ["<@",message.author.id,">, id пользователя, который ты ввёл, не похож на настоящий! Это не число!"]
                            await message.channel.send("".join(map(str,answer)))
                            await message.delete()
                            print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | id - не число | ",err)
                        #проверяю, есть ли такой id среди мемберов сервера
                        for member in message.guild.members:
                            if voteId == member.id:
                                trueId = True
                                break
                        if trueId == False:
                            answer = ["<@",message.author.id,">, я не нашёл этого пользователя на сервере!"]
                            await message.channel.send("".join(map(str,answer)))
                            await message.delete()
                            print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | голосуемый не найден в базе данных")
                        else:
                            #проверяю, голосует ли юзер за себя
                            if voteId == message.author.id:
                                answer = ["<@",message.author.id,">, голосовать можно только за кого-то другого!"]
                                await message.channel.send("".join(map(str,answer)))
                                await message.delete()
                                print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | юзер голосует за себя")
                            else:
                                #проверяю, не может ли быть голосуемый ботом
                                if voteId in botlist:
                                    answer = ["<@",message.author.id,">, это бот, за них голосовать нельзя!"]
                                    await message.channel.send("".join(map(str,answer)))
                                    await message.delete()
                                    print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | голосуемый оказался ботом")
                                else:
                                    #запрашиваю у базы данных голосовал ли юзер сегодня и когда в последний раз
                                    cursor.execute(f"""SELECT voted,lastvotedate FROM users WHERE id={message.author.id}""")
                                    votePossibility = cursor.fetchone()
                                    #проверяю голосовал ли сегодня юзер
                                    date = datetime.date.today()
                                    canVote = False
                                    #если юзер имеет в базе данных актуальную дату тогда смотрим создавал ли голосование
                                    if votePossibility[1] == date:
                                        #если да то отменяем
                                        if votePossibility[0] == 1:
                                            answer = ["<@",message.author.id,">, ты сегодня уже организовывал голосование!"]
                                            await message.channel.send("".join(map(str,answer)))
                                            await message.delete()
                                            print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | юзер уже организовывал голосование")
                                        #если нет то разрешаем
                                        elif votePossibility[0] == 0:
                                            canVote = True
                                    #если проверку прошел идём дальше
                                    if canVote:
                                        #убираем лишнее из полученных баллов
                                        score = votingDetails[2].strip('+-')
                                        errorFound = False
                                        #пытаемся перевести в целое число баллы
                                        try:
                                            score = int(score)
                                        except Exception as err:
                                            answer = ["<@",message.author.id,">, ошибка при вводе команды! Скорее всего в баллах есть буквы."]
                                            await message.channel.send("".join(map(str,answer)))
                                            await message.delete()
                                            errorFound = True
                                            print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | ошибка при переводе в целое число | ", err)
                                        #если ошибок не было идём дальше
                                        if not(errorFound):
                                            #здёсь переводятся баллы в целое число чтобы работать с ними было проще
                                            #если начинается с плюса - значит добавляем
                                            if votingDetails[2].startswith("+"):
                                                voteType = 1
                                                #смотрим чтобы не было превышения
                                                if score > 30:
                                                    answer = ["<@",message.author.id,">, как бы я хотел накрутить себе 999999999 баллов :с Но нельзя! Не больше 30 при голосовании на добавление!"]
                                                    await message.channel.send("".join(map(str,answer)))
                                                    await message.delete()
                                                    print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | превышение лимита голосования")
                                                else:
                                                    #неприятно всех уведомляем о голосовании :)
                                                    answer = ["@here! ",message.author.display_name," организовал голосование!\nРешается: добавить ли ",score, " баллов гражданину ",votingDetails[1],"\nВремя голосования: 2 минуты."]
                                                    voteMessage = await message.channel.send("".join(map(str,answer)))
                                                    #добавляем реакции для голосования
                                                    await voteMessage.add_reaction("✅")
                                                    await voteMessage.add_reaction("❌")
                                                    #пробуем запустить таймер и если не получается заметаем следы
                                                    try:
                                                        voteTimer.start(message.channel,voteId,message.author.id,voteType,score, voteMessage)
                                                    except:
                                                        answer = ["Ой!\n<@",message.author.id,"> , кто-то успел начать голосование до тебя!"]
                                                        await message.channel.send("".join(map(str,answer)))
                                                        await voteMessage.delete()
                                                        await message.delete()
                                                        print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | таймер голосования уже запущен")
                                            #если начинается с минуса - значит лишаем баллов
                                            elif votingDetails[2].startswith("-"):
                                                voteType = 0
                                                #смотрим чтобы не было превышения
                                                if score > 25:
                                                    answer = ["<@",message.author.id,">, ого! А не слишком ли жестоко? Давай договоримся, что на таких голосованиях снимаем максимум 25 баллов! Вас ведь много!"]
                                                    await message.channel.send("".join(map(str,answer)))
                                                    await message.delete()
                                                    print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | превышение лимита голосования")
                                                else:
                                                    #неприятно всех уведомляем о голосовании :)
                                                    answer = ["@here! ",message.author.display_name," организовал голосование!\nРешается: лишить ли ",score, " баллов гражданина ",votingDetails[1],"\nВремя голосования: 2 минуты."]
                                                    voteMessage = await message.channel.send("".join(map(str,answer)))
                                                    #добавляем реакции для голосования
                                                    await voteMessage.add_reaction("✅")
                                                    await voteMessage.add_reaction("❌")
                                                    #пробуем запустить таймер и если не получается заметаем следы
                                                    try:
                                                        voteTimer.start(message.channel,voteId,message.author.id,voteType,score, voteMessage)
                                                    except:
                                                        answer = ["Ой!\n<@",message.author.id,"> , кто-то успел начать голосование до тебя!"]
                                                        await message.channel.send("".join(map(str,answer)))
                                                        await voteMessage.delete()
                                                        await message.delete()
                                                        print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | таймер голосования уже запущен")
                                            else:
                                                #юзер забыл знак - уведомляем об этом!
                                                answer = ["<@",message.author.id,">, ошибка при вводе команды! Кажется у тебя нет знака в баллах."]
                                                await message.channel.send("".join(map(str,answer)))
                                                await message.delete()
                                                print(datetime.datetime.now()," | ",message.author," | неудачный запрос .vote | нет знака в количестве баллов")
            #чисто для логов
            print(datetime.datetime.now()," | ",message.author," | команда .vote выполнена.",)
        elif typeOfCommand == "help":
            #все бы было в одну команду...
            await message.channel.send("",embed=embedHelp)
            #логи
            print(datetime.datetime.now()," | ",message.author," | команда .help выполнена.",)

#таймер для команды
@tasks.loop(seconds = 60.0,count = 2)
async def voteTimer(channel, voteId, authorId, action, score, voteMessage):
    print(datetime.datetime.now(),' | таймер команды .vote запущен')
    #держим бота в курсе что идёт таймер и лезть не надо
    global activeVote
    activeVote = True
    #сделали второй круг - идём считать голоса
    #я не смог заставить это работать после цикла поэтому он делает всё на второй
    if voteTimer.current_loop == 1:
        #бот забирает сообщение из дискорда и считает сколько реакций на сообщении
        voteMessage = await channel.fetch_message(voteMessage.id)
        voteReactions = voteMessage.reactions
        voteYes = get(voteMessage.reactions, emoji="✅")
        voteNo = get(voteMessage.reactions, emoji="❌")
        doChanges = False
        #здесь решается судьба                          
        if (voteYes.count - 1) > (voteNo.count - 1):
            answer = ["<@",authorId,">, Результаты голосования:\nПредпринимаем действия..."]
            await channel.send("".join(map(str,answer)))
            doChanges = True
            print(datetime.datetime.now(),' | результат голосования => голосов "за" больше')
        elif (voteYes.count - 1) == (voteNo.count - 1):
            #внутри ситуации равенства голосов проверка что хоть кто-то проголосвал
            if (voteYes.count - 1) == 0 and (voteNo.count - 1) == 0:
                await channel.send("Никто не поучаствовал в моём голосовании :с")   #я писал бота не чтобы его игнорили!
                print(datetime.datetime.now(),' | результат голосования => никто не голосовал')
            else:
                if action == 0:
                    #демократия - это равенство их голосов
                    answer = ['<@',authorId,'>, Результаты голосования:\nГолосов набрано поровну, так как голосуют за лишение баллов, то ничего не изменится.\nЕсли нужно лишить баллов, то нужно точно набрать больше голосов "за"!']
                    await channel.send("".join(map(str,answer)))
                    print(datetime.datetime.now(),' | результат голосования => голосов поровну но игнор')
                else:
                    answer = ["<@",authorId,">, Результаты голосования:\nПредпринимаем действия..."]
                    await channel.send("".join(map(str,answer)))
                    doChanges = True
                    print(datetime.datetime.now(),' | результат голосования => голосов поровну но действуем')
        elif (voteYes.count - 1) < (voteNo.count - 1):
            #сообщение которое никто не хочет видеть
            answer = ["<@",authorId,">, Результаты голосования:\nК сожалению, голосов против набрано больше!"]
            await channel.send("".join(map(str,answer)))
            print(datetime.datetime.now(),' | результат голосования => голосов "против" больше')
        else:
            #наверное это сработает если удалить сообщение голосования?
            answer = ["<@",authorId,">, Что-то пошло не так с голосованием!"]
            await channel.send("".join(map(str,answer)))
            print(datetime.datetime.now(),' | неудачное голосование | что-то пошло не так')
        if doChanges:
            #здесь происходит базоданная движуха
            cursor.execute(f"""SELECT score FROM users WHERE id={voteId}""")
            newScore = cursor.fetchone()
            #решаю какой будет новый социальный рейтинг и в какую сторону изменится
            if action == 1:
                newScore = newScore[0] + score
            else:
                newScore = newScore[0] - score
            data = (newScore,voteId)
            cursor.execute("""UPDATE users SET score=? WHERE id=?""",data)
            conn.commit()
            #надо уведомить юзера что его счёт теперь другой
            cursor.execute(f"""SELECT score FROM users WHERE id={voteId}""")
            score = cursor.fetchone()
            rank = findRating(score[0])
            messageEmbed = findRatingPicture(rank)
            answer = ["<@",voteId,">, твой социальный рейтинг теперь: ",score[0],"!\nТвой ранг: ",rank,"!"]
            await channel.send("".join(map(str,answer)), embed = messageEmbed)
        else:
            pass
        #сохраняем факт что произошло голосование
        sqlDate = datetime.datetime.now().strftime("%Y-%m-%d")
        data = (sqlDate,authorId)
        cursor.execute(f"""UPDATE users SET voted={1} WHERE id={authorId}""")
        cursor.execute("""UPDATE users SET lastvotedate=? WHERE id=?""",data)
        conn.commit()
        activeVote = False
        print(datetime.datetime.now()," | таймер команды .vote выключен.",)

#функция, которая возращает рейтинг в команде .credits
def findRating(score):
    if score >= 5000:
        return "AAA"
    elif score >= 2500:
        return "AA"
    elif score >= 1000:
        return "A"
    elif score >= 750:
        return "B"
    elif score < 750:
        return"C"

#функция, которая возвращает ембед с картинкой рейтинга
def findRatingPicture(rating):
    if rating == "AAA":
        return discord.Embed().set_image(url="https://i.imgur.com/ROi2Y3z.png")
    elif rating == "AA":
        return discord.Embed().set_image(url="https://i.imgur.com/j94yj2r.png")
    elif rating == "A":
        return discord.Embed().set_image(url="https://i.imgur.com/yIdlIUa.png")
    elif rating == "B":
        return discord.Embed().set_image(url="https://i.imgur.com/V73IHbF.png")
    elif rating == "C":
        return discord.Embed().set_image(url="https://i.imgur.com/rEfwGuM.png")

client.run("YOUR TOKEN HERE")   #здесь вписывай свой токен бота