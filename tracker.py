
from aiogram import types, Dispatcher, Bot
from aiogram.filters import Command
from aiogram.types import Message, LinkPreviewOptions
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State

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
            await self.cursor.execute('insert into addresses (address, user) values (?, ?)', (address, user_id))
            await self.connect.commit()
            
        async def delete(self, address, user_id):
            await self.cursor.execute('delete from addresses where address = ? and user = ?', (address, user_id,))
            await self.connect.commit()
            
        async def require_user(self, address, user_id):
            await self.tools()
            await self.cursor.execute('select * from addresses where address = ? and user = ?', (address, user_id))
            return await self.cursor.fetchone()
        
            
    except aiosqlite.Error as e:
        log(f'{e}')
        
class setState(StatesGroup):
    track_wallet = State()
    untrack_address = State()
    track_wallet_edit = State()
     
class Wallet(Table):   
    @dp.message(Command('start'))
    async def start(message: types.Message):
        await message.answer(
            f'Hello! This tracker for Ethereum.'
            'if tracking wallet, send me command a /track'
        )
        
    @dp.message(Command('track'))
    async def track_wallet(message: types.Message, state: FSMContext):
        await message.reply('Send your wallet address!')
        await state.set_state(setState.track_wallet)
        
    @dp.message(Command('untrack'))
    async def untrack_wallet(message: types.Message, state: FSMContext):
        await message.reply('Which address untrack for you?')
        await state.set_state(setState.untrack_address)
    
    async def track_scanner(self, address, user_id):
        hash_set = set()
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
                                
            log(f'search transactions...')
            await asyncio.sleep(3)
            
            
    @dp.message(setState.track_wallet)
    async def track_wallet_edit(message: Message, state: FSMContext):
        
        address = message.text
        user_id = message.from_user.id
        added = await message.answer('Added address...')
        user_list = await tab.require_user(address, user_id)
        
        if not address.startswith('0x'):
                await message.reply('Only 0x-format address tracking!')
                return
            
        else:
            pass
        
        if user_list is None:
            await asyncio.sleep(1)
            await tab.add(address, user_id)
            await message.answer('Your address successfully added!')
            await message.answer('Search transactions...')
            
        else:
            await message.answer('This address already tracking!')
        
        asyncio.create_task(wal.track_scanner(address, user_id))
        await bot.delete_message(chat_id=message.chat.id, message_id=added.message_id)
        await asyncio.sleep(5)
        await tab.connect.close()
        await state.set_state(setState.track_wallet_edit)
        
    @dp.message(setState.untrack_address)
    async def untrack_wallet_edit(message: Message, state: FSMContext):
        
        address = message.text
        user_id = message.from_user.id
        wait = await message.answer('Untrack address...')
        user_list = await tab.require_user(address, user_id)
            
        if user_list is None:
            await message.reply('Your address not found to list, add his!')
            return
                
        else:
            await asyncio.sleep(1)
            await tab.delete(address, user_id)
            await message.answer('Your address successfully untracking!')
        
        await bot.delete_message(chat_id=message.chat.id, message_id=wait.message_id)
        await tab.connect.close()
             
tab = Table()
wal = Wallet()

async def main():
    await dp.start_polling(bot)
  
if __name__ == "__main__":
        asyncio.run(main())    
