import discord
from discord.ext import commands
import random
import string

PREFIX = "c!"

class Game:
    def __init__(self, mode):
        self.mode = mode  # "collaborative" or "word"
        self.chain = []   # List of submitted letters/words/spaces
        self.current_fragment = ""  # Current string being built in collaborative mode
        self.used_words = set()  # Completed words

    def add_letter(self, letter):
        """Add a letter to the current fragment in collaborative mode"""
        self.current_fragment += letter
        self.chain.append(letter)
        return self.current_fragment

    def add_space(self):
        """Add a space to separate words in collaborative mode"""
        # Add the current fragment as a completed word (if not empty)
        if self.current_fragment:
            self.used_words.add(self.current_fragment)
            completed_word = self.current_fragment
            self.current_fragment = ""
            self.chain.append(" ")
            return True, completed_word
        return False, None

    def add_word(self, word):
        """Add a word in word chain mode"""
        self.chain.append(word)
        self.used_words.add(word.lower())
        return word[-1].lower()  # Return last letter for next word

    def get_chain_text(self):
        """Get the current game state as text"""
        if self.mode == "collaborative":
            return "".join(self.chain)
        else:  # word mode
            return " → ".join(self.chain)

    def get_completed_words(self):
        """Get list of completed words"""
        return list(self.used_words)

# Active games stored by channel ID
active_games = {}

# Enable the message content intent
intents = discord.Intents.default()
intents.message_content = True

# Bot setup
bot = commands.Bot(command_prefix=PREFIX, intents=intents, help_command=None)

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")
    await bot.change_presence(activity=discord.Game(name=f"c!help"))

def get_game(channel):
    return active_games.get(channel.id, None)

@bot.command(name="start")
async def start(ctx, mode: str = "collaborative", channel: discord.TextChannel = None):
    """
    Start a new word chain game
    Usage: c!start [mode] [channel]
    Modes: collaborative (default), word
    """
    target_channel = channel or ctx.channel

    mode = mode.lower()
    if mode not in ["collaborative", "word"]:
        await ctx.send("Invalid mode! Please choose either **collaborative** or **word**.")
        return

    if target_channel.id in active_games:
        await ctx.send(f"A game is already running in {target_channel.mention}!")
        return

    game = Game(mode)

    if mode == "collaborative":
        # Start with a random letter for collaborative mode
        start_letter = random.choice(string.ascii_lowercase)
        game.current_fragment = start_letter
        game.chain.append(start_letter)

        await target_channel.send(
            f"**Collaborative Word Building Game Started!**\n"
            f"Starting with letter: **{start_letter.upper()}**\n"
            f"Current word fragment: **{game.current_fragment}**\n\n"
            f"Commands: Use `{PREFIX}s <letter>` to add a letter to build a word together.\n"
            f"Use `{PREFIX}sp` or `{PREFIX}space` to complete the current word and start a new one."
        )
    else:  # word mode
        start_word = random.choice(["I", "A", "An", "My", "The", "This", "That", "Those", "These", "He", "She"])
        game.chain.append(start_word)
        game.used_words.add(start_word.lower())
        last_letter = start_word[-1].lower()

        await target_channel.send(
            f"**Word Chain Game Started!**\n"
            f"Starting word: **{start_word}**\n"
            f"Next word must start with: **{last_letter.upper()}**\n\n"
            f"Command: Use `{PREFIX}s <word>` to submit a word."
        )

    active_games[target_channel.id] = game

    if channel and channel != ctx.channel:
        await ctx.send(f"Game started in {target_channel.mention}.")

@bot.command(name="stop")
async def stop(ctx, channel: discord.TextChannel = None):
    """
    Stop a running game
    Usage: c!stop [channel]
    """
    target_channel = channel or ctx.channel

    if target_channel.id not in active_games:
        await ctx.send(f"No active game found in {target_channel.mention}.")
        return

    game = active_games[target_channel.id]

    # Show final results before stopping the game
    if game.mode == "collaborative":
        # Make sure to add the current fragment as a word if it's not empty
        if game.current_fragment:
            game.used_words.add(game.current_fragment)

        words_list = ", ".join(game.get_completed_words()) if game.get_completed_words() else "No words completed"
        final_chain = game.get_chain_text()

        await ctx.send(
            f"🏁 **Game Finished!**\n"
            f"Final text: **{final_chain}**\n"
            f"Words created: {words_list}"
        )
    else:
        final_chain = game.get_chain_text()
        words_count = len(game.used_words)

        await ctx.send(
            f"🏁 **Game Finished!**\n"
            f"Final word chain: **{final_chain}**\n"
            f"Total words: {words_count}"
        )

    del active_games[target_channel.id]
    await ctx.send(f"Game stopped in {target_channel.mention}.")

@bot.command(aliases=["s", "submit"])
async def submit_letter_or_word(ctx, *, submission: str):
    """
    Submit a letter (in collaborative mode) or a word (in word mode)
    Usage: c!s <letter/word> OR c!submit <letter/word>
    """
    game = get_game(ctx.channel)
    if not game:
        await ctx.send(f"No active game in this channel. Start one with `{PREFIX}start`.")
        return

    submission = submission.strip().lower()

    if game.mode == "collaborative":
        # In collaborative mode, only accept single letters
        if len(submission) != 1 or submission not in string.ascii_lowercase:
            await ctx.send("Please submit a single alphabetical letter.")
            return

        # Add the letter
        current_word = game.add_letter(submission)

        await ctx.send(
            f"✅ Letter added! Current word: **{current_word}**\n"
            f"Continue building or use `{PREFIX}sp` to complete this word."
        )

    else:  # word mode
        if not submission.isalpha() or len(submission) < 1:
            await ctx.send("Please submit a valid word (alphabetical).")
            return

        if submission in game.used_words:
            await ctx.send("❌ This word has already been used!")
            return

        # Check if the word starts with the expected letter
        last_word = game.chain[-1]
        expected_letter = last_word[-1].lower()

        if submission[0] != expected_letter:
            await ctx.send(f"❌ Your word should start with **{expected_letter.upper()}**.")
            return

        # Add the word to the chain
        game.add_word(submission)

        await ctx.send(
            f"✅ Word accepted! Chain is now: **{game.get_chain_text()}**\n"
            f"Next word must start with: **{submission[-1].upper()}**"
        )

@bot.command(aliases=["sp"])
async def space(ctx):
    """
    Complete the current word in collaborative mode
    Usage: c!sp OR c!space
    """
    game = get_game(ctx.channel)
    if not game:
        await ctx.send(f"No active game in this channel. Start one with `{PREFIX}start`.")
        return

    if game.mode != "collaborative":
        await ctx.send("This command is only available in collaborative word building mode.")
        return

    # Complete the current word (if any)
    word_completed, completed_word = game.add_space()

    if word_completed:
        await ctx.send(
            f"🎉 **Word completed: {completed_word}!**\n"
            f"Start building a new word.\n"
            f"Words found so far: {', '.join(game.get_completed_words())}"
        )
    else:
        await ctx.send("You need to add some letters first before completing a word.")

@bot.command()
async def status(ctx):
    """
    Show the current game status
    Usage: c!status
    """
    game = get_game(ctx.channel)
    if not game:
        await ctx.send("No active game in this channel.")
        return

    if game.mode == "collaborative":
        words_found = game.get_completed_words()
        current_chain = game.get_chain_text()

        await ctx.send(
            f"**Collaborative Word Building Game**\n"
            f"Current word: **{game.current_fragment}**\n"
            f"Full chain so far: **{current_chain}**\n"
            f"Words completed: {', '.join(words_found) if words_found else 'None yet'}\n"
            f"Use `{PREFIX}s <letter>` to add the next letter."
        )
    else:
        await ctx.send(
            f"**Word Chain Game**\n"
            f"Current chain: **{game.get_chain_text()}**\n"
            f"Next word must start with: **{game.chain[-1][-1].upper()}**\n"
            f"Words used: {len(game.used_words)}"
        )

@bot.command()
async def help(ctx):
    """
    Display the commands for the bot
    Usage: c!help
    """
    help_text = (
        "**Discord Word Chain Game Commands**\n\n"
        f"`{PREFIX}start [mode] [channel]` – Start a new game (modes: collaborative, word)\n"
        f"`{PREFIX}stop [channel]` – Stop the game in the specified channel (or current channel)\n"
        f"`{PREFIX}s` or `{PREFIX}submit <letter/word>` – Submit a letter or word depending on game mode\n"
        f"`{PREFIX}sp` or `{PREFIX}space` – Complete the current word and start a new one\n"
        f"`{PREFIX}status` – Check the current game status\n"
        f"`{PREFIX}help` – Display this help message\n\n"
        "**Game Modes:**\n"
        "• **Collaborative** – Players add one letter at a time to build words together\n"
        "• **Word** – Players submit full words where each word must start with the last letter of the previous word"
    )
    await ctx.send(help_text)

# Replace with your token
TOKEN = "TOKEN"
bot.run(TOKEN)
