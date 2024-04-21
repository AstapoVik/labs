from aiogram import Bot, Dispatcher, executor, types
from config import BOT_API_TOKEN
from PIL import Image
import easyocr
import re
import hashlib
import io
import pymongo




client = pymongo.MongoClient("mongodb+srv://arknim:gogiliop@cluster0.hrr8k4l.mongodb.net/?retryWrites=true&w=majority")
db = client.bot_tg
collection = db.data_user



reader = easyocr.Reader(['en','ru'], gpu = False)



dict = {}


bot = Bot(BOT_API_TOKEN)
dp = Dispatcher(bot)

@dp.message_handler(content_types=['sticker'])
async def sendAnswer(message: types.Message)->None:

    if message.sticker.is_animated == True or message.sticker.is_video == True:
        await message.answer(text="The sticker is not static")
        return None

    file_id = message.sticker.file_id
    file_unique_id = message.sticker.file_unique_id
    user_id = message.from_user.id

    initDictionaryForUser( user_id )
    

    file = await bot.get_file(file_id)

    bytesImg = io.BytesIO()
    await bot.download_file( file.file_path, bytesImg )



    with Image.open( io.BytesIO( bytesImg.getvalue() ) ) as img:
        img.save( bytesImg, format='png')



    text_img = GetTextFromImage( bytesImg.getvalue() )


    if text_img != "":
        await message.answer(text=text_img)

        if dict.get( file_unique_id ) == None:
            dict[file_unique_id] = { "text": text_img.lower(), "file_id": file_id }
            collection.update_one( { "_id": user_id }, {"$set": {"stickers": dict } } )

    else:
        await message.answer(text="Text on sticker not found")







@dp.message_handler(content_types=['text'])
async def sendAnswer(message: types.Message):

    initDictionaryForUser( message.from_user.id )

    files = searchFilesInDict(message.text)

    if( len(files) == 0 ):
        await message.answer("sticker not found")
    else:
        for file in files:
            await message.answer_sticker(file)



@dp.inline_handler()
async def inline_answer(query: types.InlineQuery):
    text = query.query or 'echo'
    result_id = hashlib.md5(text.encode()).hexdigest()

    initDictionaryForUser( query.from_user.id )


    files = searchFilesInDict(text)


    stickers = [ types.InlineQueryResultCachedSticker(
            id=''.join( [ result_id, str(id) ] ),
            sticker_file_id=files[id],
        ) for id in range(0,len(files)) ]



    await bot.answer_inline_query(
        inline_query_id=query.id,
        results=stickers,
        cache_time=1
    )




def initDictionaryForUser(user_id):

    jsonData = collection.find_one({ "_id": user_id })

    global dict
    if( jsonData == None ):
        collection.insert_one( {"_id": user_id, "stickers": {} } )
        dict = {}
    else:
        dict = jsonData['stickers']
  
  




def GetTextFromImage(imgBytes):
    return ' '.join( bound[1] for bound in reader.readtext(imgBytes) )


def searchFilesInDict(word):
    return list(filter( lambda key: key != '', [ dict[key]['file_id'] if re.search(word, dict[key]['text']) != None else '' for key in dict.keys() ] ))








if __name__ == "__main__":
    executor.start_polling(dp)
