from aiogram import types, Dispatcher, Bot
from aiogram.filters import Command
from aiogram.types import Message, LinkPreviewOptions
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram import F
from web3 import AsyncWeb3, AsyncHTTPProvider
from web3.exceptions import TransactionNotFound

import asyncio
import aiosqlite
import logging
logging.basicConfig(level=logging.INFO, format="%(message)s")
log = logging.info


api = ''
token_bot = ''

dp = Dispatcher()
bot = Bot(token=token_bot)
w3 = AsyncWeb3(AsyncHTTPProvider(api))
buttons = InlineKeyboardMarkup(inline_keyboard=[])


class Table():
    def __init__(self, address='', cursor='', connect='', user_id='', block=''):
        self.address = address
        self.cursor = cursor
        self.connect = connect
        self.user_id = user_id
        self.block = block

    try:
        async def tools(self):
            self.connect = await aiosqlite.connect('addresses.db')
            self.cursor = await self.connect.cursor()

        async def create(self):
            await self.tools()
            await self.cursor.execute('create table if not exists addresses (address TEXT, user INTEGER)')
            await self.connect.commit()       
        
        async def add(self, address, user_id):
            await self.cursor.execute('insert or ignore into addresses (address, user) values (?, ?)', (address, user_id))
            await self.connect.commit()
            
        async def delete(self, address, user_id):
            await self.cursor.execute('delete from addresses where address = ? and user = ?', (address, user_id))
            await self.connect.commit()
            
        async def require_user(self, address, user_id):
            await self.cursor.execute('select count(*) from addresses where address = ? and user = ?', (address, user_id))
            result = await self.cursor.fetchone()
            num = result[0]
            return num
            
    except aiosqlite.Error as e:
        log(f'{e}')
        
class setState(StatesGroup):
    track_wallet = State()
    untrack_address = State()
    track_wallet_edit = State()

inline_keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text='➕ Track', callback_data='/track'), 
         InlineKeyboardButton(text='❌ Untrack', callback_data='/untrack'),
         InlineKeyboardButton(text='📒 Wallets', callback_data='/my_wallets')]], input_field_placeholder='Use the menu a below...')

@dp.message(Command('start'))
async def start(message: types.Message):
    await message.answer(
        f'Hello! This tracker for Ethereum.\n'
        f'If tracking wallet, use a button under.\n', reply_markup=inline_keyboard
    )
        
@dp.callback_query(F.data == '/track')
async def track_wallet(callback: CallbackQuery, state: FSMContext):
    await callback.message.reply('Send your wallet address!', reply_markup=inline_keyboard)
    await state.set_state(setState.track_wallet)
    
@dp.callback_query(F.data == '/untrack')
async def untrack_wallet(callback: CallbackQuery, state: FSMContext):
    await callback.message.reply('Which address untrack for you?', reply_markup=inline_keyboard)
    await state.set_state(setState.untrack_address)

@dp.callback_query(F.data == '/my_wallets') 
async def get_wallets(callback: CallbackQuery):
    user_id = callback.from_user.id
    await tab.cursor.execute('select * from addresses where user = ?', (user_id, ))
    memory = await tab.cursor.fetchall()
    
    data_addresses = []
    
    if memory: 
        for address in memory:
            data_addresses += f'{address[0]}\n\n'
            await callback.message.reply(f'Your addresses - \n\n'
                                f'{data_addresses}'
                                )
    else: 
        await callback.message.reply('Your dont have address!')

    
async def track_scanner(address, user_id):
    log(f'search transactions...')
    hash_set = []
    
    while True: 
        try:  
            block = await w3.eth.get_block('latest', full_transactions=True)
            transactions = block['transactions']
            
            for txn in transactions:
                hash_id = txn.get('hash').hex()
                sender = txn.get('from')
                recipient = txn.get('to')                
                            
                if sender == address or recipient == address:
                    trackable = address
                    
                    if hash_id in hash_set:
                        continue
                    
                    else:
                        url = (f"https://sepolia.etherscan.io/tx/0x{hash_id}")
                        replies = (f'🚨 Found transaction! 🚨\n\n'
                            f'👤 Account : {trackable}\n\n'
                            f'🔗 URL: {url}'
                            )
                        await bot.send_message(chat_id=user_id, text=replies, link_preview_options=LinkPreviewOptions(is_disabled=True), parse_mode='html')
                        hash_set.add(hash_id)
                        
        except TransactionNotFound as e:
            log(f'{e}')
        await asyncio.sleep(3)

@dp.callback_query()
async def button_handler(callback: CallbackQuery, state: FSMContext):
    if callback.data == 'Track':
        await track_wallet_edit(callback, state)
    
    if callback.data == 'Untrack':
        await untrack_wallet_edit(callback, state)
        
@dp.message(setState.track_wallet)
async def track_wallet_edit(message: Message, state: FSMContext):
    address = message.text
    user_id = message.from_user.id
    added = await message.answer('Added address...')
    
    require = await tab.require_user(address, user_id)
    
    if not address.startswith('0x'):
            await message.reply('Only 0x-format address tracking!')
            return
    else:
        pass
    
    if require > 0:
        await message.answer('This address already tracking!')
    else:
        await asyncio.sleep(1)
        await tab.add(address, user_id)
        await message.answer('Your address successfully added!')
        await message.answer('Search transactions...')
    
    asyncio.create_task(track_scanner(address, user_id))
    await bot.delete_message(chat_id=message.chat.id, message_id=added.message_id)
    await asyncio.sleep(5)
    await state.set_state(setState.track_wallet_edit)
    await tab.connect.commit()
    
        
@dp.message(setState.untrack_address)
async def untrack_wallet_edit(message: Message, state: FSMContext):
    address = message.text
    user_id = message.from_user.id
    deleted = await message.answer('Untrack address...')
    
    require = await tab.require_user(address, user_id)
    
    if require > 0:
        await asyncio.sleep(1)
        await tab.delete(address, user_id)
        await message.answer('Your address successfully untracking!')
        await bot.delete_message(chat_id=message.chat.id, message_id=deleted.message_id)
        await tab.connect.commit()
        
    else:
        await message.reply('Your address not found to list, add his')
    
                         
tab = Table()

async def main():
    await tab.tools()
    await tab.create()
    await dp.start_polling(bot)
  
if __name__ == "__main__":
        asyncio.run(main())    