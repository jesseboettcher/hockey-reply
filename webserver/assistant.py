from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from enum import Enum
from flask import current_app
import json5
import openai
import os
import phonenumbers
import pickle
import re
from rich.console import Console, Style
from zoneinfo import ZoneInfo

from webserver.database.alchemy_models import GameReply, User, Team
from webserver.database.hockey_db import get_db, PersonReference
from webserver.sms import SMS
from webserver.utils import timeuntil

# Load environment variables from .env file
load_dotenv('keys/.env')

openai.api_key = os.getenv("OPENAI_API_KEY")

# Save data paths
SAVE_DATA_DIR = './data'
SAVE_DATA_PATH = f"{SAVE_DATA_DIR}/assistant_captain.pkl"
LOG_DATA_DIR = './logs'

# Debug
PRINT_INPUTS = False
PRINT_OUTPUTS = False
MESSAGES_COUNTER = 1
LIVE_DATA = False # if True, assistant will write to database with game replies

# Constants
ASSISTANT_ASSIGNED_ANON_SUB_ID = -100
GPT_CHARACTER_LIMIT = 15000 # assuming avg 5 characters per token to a limit of 3k tokens (1k token buffer to hard limit of 4k)

console = Console()
debug_style = Style(color="grey42", bold=False)
asst_style = Style(color="sky_blue3")

### TEST DATA ###
placeholder_team_id = 247 # Hardcoded for initiating goalie search via SMS which is not yet ready for prod

placeholder_next_game = {
    'game_id': 1,
    'scheduled_at': timedelta(hours=18) + datetime.now(timezone.utc),
    'team_id': placeholder_team_id,
}

std_system_message = f"""
            You are an assistant captain of a hockey team.;
            You are from Letterkenny, Ontario and speak with a Canadian accent.;
            The team plays in San Jose California at Sharks Ice;
            You have a list of goalies that you can use to find a someone to play goalie for a game;
            You are responsible for making sure the team has a goalie for each game;
            Be informal and brief. Abbreviations are ok.;
            You enjoy joking around and chatting about hockey, but are not very talkative.;
        """

sub_goalie_system_message = f"""
            Your name is Assistant Captain GPT and you are an assistant captain of a hockey team whose job is to make sure there is a goalie for each game.;
            You are from Letterkenny, Ontario and with a Canadian accent.;
            The team plays in San Jose California at Sharks Ice;
            Assume the player is familiar with the team and people on it;
        """

# Types of classifying messages received from captains and goalies
class ConversationMessageTypes(Enum):
    chat = 1
    sub_goalie_request = 2
    sub_goalie_request_confirming_which_game = 3

class GoalieConversationMessageTypes(Enum):
    confirmed = 1
    declined = 2
    need_more_time = 3
    unknown = 4

# Types for classifying responses to specific questions
class ConfirmationMessageTypes(Enum):
    yes = 0
    no = 1

class GoalieSearch:
    """
    Class to hold state of a goalie search.
    """
    class State(Enum):
        unresolved = 0
        complete_goalie_found = 1
        complete_no_goalie = 2

    def __init__(self, team_id, game_id, scheduled_at):
        self.game_id = game_id
        self.team_id = team_id
        self.scheduled_at = scheduled_at
        self.messages = {} # goalie name -> list of messages
        self.state = GoalieSearch.State.unresolved
    
        self.captains = []
        db = get_db()
        team = db.get_team_by_id(self.team_id)
        for player in team.players:
            if player.role == 'captain':
                self.captains.append(PersonReference(player.user_id, None, None))

        goalies = []
        for goalie in team.goalies:
            goalies.append(PersonReference(goalie.user_id, goalie.nickname, goalie.phone_number))

        self.goalie_state = {key: GoalieConversationMessageTypes.unknown for key in goalies} # goalie name -> state [unknown, confirmed, declined, waiting_on_response]

    def is_expired(self):
        """
        Check if the search has expired.
        """
        return self.scheduled_at < datetime.now(timezone.utc)

    def is_goalie_confirmed(self):
        """
        Check if a goalie has been confirmed.
        """
        return GoalieConversationMessageTypes.confirmed in self.goalie_state.values()

    def set_goalie_confirmed(self, goalie):
        """
        Set a goalie's state to confirmed.
        """
        self.goalie_state[goalie] = GoalieConversationMessageTypes.confirmed
        self.state = GoalieSearch.State.complete_goalie_found

        if LIVE_DATA:
            user_id = goalie.user_id
            if user_id is None or user_id == 0:
                user_id = ASSISTANT_ASSIGNED_ANON_SUB_ID
            db = get_db()
            db.set_game_reply(self.game_id, self.team_id, user_id, 'yes',
                              'set by assistant captain gpt', True)

    def set_goalie_declined(self, goalie):
        """
        Set a goalie's state to declined.
        """
        self.goalie_state[goalie] = GoalieConversationMessageTypes.declined

        if LIVE_DATA:
            user_id = goalie.user_id
            if user_id is None or user_id == 0:
                pass # anon subs do not need to reply NO, only YES
            else:
                db = get_db()
                db.set_game_reply(self.game_id, self.team_id, user_id, 'no',
                                  'set by assistant captain gpt', False)

        if self.next_goalie() is None:
            self.state = GoalieSearch.State.complete_no_goalie

    def next_goalie(self):
        """
        Go through goalies and return name of next goalie
        whose state is not confirmed or declined.
        """
        for goalie, state in self.goalie_state.items():
            if state != GoalieConversationMessageTypes.confirmed and state != GoalieConversationMessageTypes.declined:
                return goalie

def get_user_id_for_phone_number(phone_number):
    """
    Get a user id for a phone number.
    """
    db = get_db()
    users = db.get_users()
    for user in users:
        if user.phone_number and phonenumbers.parse(user.phone_number, "US") == phone_number:
            return user.user_id
    return None

def create_goalie_search_for_next_goalieless_game(team_id):
    """
    Get the game id for the next game for a team that does not have a goalie.
    """
    if os.getenv('HOCKEY_REPLY_ENV') != 'prod': # TODO remove hardcoded TEST GAME
        return GoalieSearch(placeholder_next_game["team_id"], placeholder_next_game["game_id"], placeholder_next_game["scheduled_at"])

    db = get_db()
    games = db.get_games_for_team(team_id)

    for game in games:

        if game.completed == 1 or game.scheduled_at < datetime.now(timezone.utc):
            continue

        replies = db.game_replies_for_game(game.game_id, team_id)

        goalie_confirmed = False
        goalie_declined = False
        for reply in replies:
            
            if reply.is_goalie and reply.response == 'no':
                goalie_declined = True

            if reply.is_goalie and reply.response == 'yes':
                goalie_confirmed = True
                break
        
        if goalie_confirmed: # check the next game
            continue

        goalie_seach = GoalieSearch(team_id, game.game_id, game.scheduled_at)

        if goalie_declined:
            goalie_seach.set_goalie_declined(PersonReference(reply.user_id, '', ''))

        return goalie_seach

    return None

def chat_gpt(messages, json_key, deterministic):
    """
    Chat with GPT-3. Does preprocessing to keep the conversation within GPT's max context size,
    and postprocessing to extract the message from the json response.
    """
    if PRINT_INPUTS:
        print(messages)
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        temperature=0.0 if deterministic else 0.7,
        )

    # keep the conversation within GPT's max context size. Do not delete the first message, which is the system message.
    while sum([len(msg['content']) for msg in messages]) > GPT_CHARACTER_LIMIT:
        if len(messages) == 1:
            break # system msg only
            
        del messages[1] # remove oldest message

    # the message is supposed to be json, but sometimes it's not
    ai_msg = response['choices'][0]['message']['content']
    try:
        if json_key:
            # sometimes gpt returns a bunch of text and json, so find the content between the braces
            re_result = re.search(r'\{.*?\}', response['choices'][0]['message']['content'], re.DOTALL)
            # print(f"raw: {ai_msg}")
            if re_result:
                # print(f"re result: {re_result.group(0)}")
                ai_msg = json5.loads(re_result.group(0))[json_key]
    except:
        pass

    if PRINT_OUTPUTS:
        print(ai_msg)

    # write messages to file for debugging
    global MESSAGES_COUNTER
    with open(f"{LOG_DATA_DIR}/messages_{MESSAGES_COUNTER}.json", "w") as f:
        MESSAGES_COUNTER += 1
        logs = {}
        logs['input'] = messages
        logs['output'] = response['choices'][0]['message']['content']
        logs['parsed_output'] = ai_msg
        logs['time_utc'] = datetime.now(timezone.utc).strftime('%A, %B %d, %Y %I:%M:%S %p')
        logs['time_local'] = datetime.now().strftime('%A, %B %d, %Y %I:%M:%S %p')
        json5.dump(logs, f)

    return ai_msg

def chat_gpt_analyze_conversation(messages, yes_no_question):
    """
    Chat with GPT-3 to analyze a conversation. Use GPT as a reasoning engine to
    get a true false result from a question about the provided conversation.
    """
    classify_directive = f"""
        Answer question from the following message_type list: {", ".join(type.name for type in ConfirmationMessageTypes)};
        Reply in following format, replacing the text in the <> with your answer: {{"message_type": "<answer>"}}
        Question: {yes_no_question}
    """
    messages = messages.copy()
    messages.append({"role": "system", "content": classify_directive.strip()})

    message_type = chat_gpt(messages, 'message_type', True)

    if message_type == 'yes':
        return True

    return False

class Conversation:
    """
    A conversation with a person. It is a state machine that can be in one of the following states:
        0: chat
        1: assist_captain
        2: secure_goalie
    Holds a list of messages in order to be able to chat with GPT-3.
    """

    class Goal(Enum):
        chat = 1
        assist_captain = 2
        secure_goalie = 3

    def __init__(self, person_ref):
        self.phone_number = person_ref.phone_number
        self.person_ref = person_ref
        self.state = 0
        self.goal = Conversation.Goal.chat
        self.pending_goalie_search = None
        self.messages = [] # list of messages
        self.messages.append({"role": "system", "content": std_system_message.strip()})

    def is_empty_conversation(self):
        """
        Check if the conversation has no user or assistant messages (ignores system messages)
        """
        for message in self.messages:
            if message["role"] == "user" or message["role"] == "assistant":
                return False
        return True

    def add_system_message(self, message):
        """
        Add a system message to the conversation.
        """
        self.messages.append({"role": "system", "content": message})

    def set_goal(self, goal):
        
        if goal == self.goal:
            return
        
        self.goal = goal
        if self.goal == Conversation.Goal.secure_goalie:
            self.messages.clear()
            self.messages.append({"role": "system", "content": sub_goalie_system_message.strip()})

    def receive_message(self, message):
        """
        Classify the incoming message and handle it with the appropriate request
        handler, or just to continue the chat.
        """
        console.print(f"SMS from {self.person_ref.name}: {message}")
        self.messages.append({"role": "user", "content": message})

        classification_types = ConversationMessageTypes
        if self.goal == Conversation.Goal.secure_goalie:
            classification_types = GoalieConversationMessageTypes

            if chat_gpt_analyze_conversation(self.messages, "Did this user agree to play goalie in the game?"):
                message_type = GoalieConversationMessageTypes.confirmed.name
            elif chat_gpt_analyze_conversation(self.messages, "Do you think the user is unavailable to play goalie in the game?"):
                message_type = GoalieConversationMessageTypes.declined.name
            else:
                message_type = ConversationMessageTypes.chat.name

            console.print(f"goal: {self.goal.name}, state: {self.state}, message_type: {message_type}", style=debug_style)
            return message_type

        elif self.state == ConversationMessageTypes.sub_goalie_request_confirming_which_game:
            classification_types = ConfirmationMessageTypes

        classify_directive = f"""
            You are an assistant hockey captain who speaks json; 
            Classify UserMessage from the following message_type list: {", ".join(type.name for type in classification_types)};
            Reply in following format, replacing the text in the <> with your classification: {{"message_type": "<classification>"}}
            UserMessage: {message}
        """
            # Reply with json with key message_type;
        # messages.append({"role": "system", "content": ''})

        messages = self.messages.copy()
        messages.append({"role": "system", "content": classify_directive.strip()})

        message_type = chat_gpt(messages, 'message_type', True)
        console.print(f"goal: {self.goal.name}, state: {self.state}, message_type: {message_type}", style=debug_style)
        return message_type

    def send_assistant_message(self, message):
        """
        Send a message to the user
        """
        self.messages.append({"role": "assistant", "content": message})
        self.send_message(f"Assistant Captain GPT: {message}")
        
        sms_client = SMS()
        sms_client.send([phonenumbers.format_number(self.phone_number, phonenumbers.PhoneNumberFormat.E164)], message)

    def send_message(self, message):
        """
        Send a message to the user
        """
        console.print(f"SMS to {self.person_ref.name}: {message}", style=asst_style)
        
        sms_client = SMS()
        sms_client.send([phonenumbers.format_number(self.phone_number, phonenumbers.PhoneNumberFormat.E164)], message)

    def handle_chat_message(self, message):
        """
        Handle a chat message.
        """
        self.messages.append({"role": "user", "content": message})
        
        messages = self.messages.copy()
        messages.append({"role": "system", "content": 'Reply in following format, replacing the text in the <> with your message: {"response": "<your response>"}'})

        ai_msg = chat_gpt(messages, 'response', False)
        self.send_assistant_message(ai_msg)

    def handle_captain_goalie_request(self, message):
        """
        Handle a goalie request -- for now, assume the next game that does
        not have a confirmed goalie. In the future, engage with the user to
        try to find a game.
        """
        if os.getenv('HOCKEY_REPLY_ENV') == 'prod': # TODO team+game selection required to support in prod
            messages = self.messages.copy()
            messages.append({"role": "system", "content": "Tell the user they need to press the Find Goalie button on the game page to initiate a goalie search"})
            messages.append({"role": "system", "content": 'Reply in following format, replacing the text in the <> with your message: {"response": "<your response>"}'})
            
            ai_msg = chat_gpt(messages, 'response', False)
            self.send_assistant_message(ai_msg)
            return None            

        goalie_search = create_goalie_search_for_next_goalieless_game(placeholder_team_id)

        messages = self.messages.copy()

        if goalie_search is None:
            messages.append({"role": "system", "content": "tell the user that there are no games that need a goalie"})
            messages.append({"role": "system", "content": 'Reply in following format, replacing the text in the <> with your message: {"response": "<your response>"}'})
            self.state = ConversationMessageTypes.chat
        else:
            pacific = ZoneInfo('US/Pacific')
            datetime_str = f'{goalie_search.scheduled_at.astimezone(pacific).strftime("%A at %I:%M %p")}'
            time_until = timeuntil(datetime.now(timezone.utc).astimezone(pacific), goalie_search.scheduled_at.astimezone(pacific)).replace(' ', ' ')

            messages.append({"role": "system", "content": f"tell the user that the game on {datetime_str} in {time_until} needs a goalie; Ask for the user to authorize a sub goalie search"})
            messages.append({"role": "system", "content": 'Reply in following format, replacing the text in the <> with your message: {"response": "<your response>"}'})
            self.state = ConversationMessageTypes.sub_goalie_request_confirming_which_game
            self.pending_goalie_search = goalie_search

        ai_msg = chat_gpt(messages, 'response', False)
        self.send_assistant_message(ai_msg)

        return goalie_search

    def handle_captain_goalie_request_confirming_game(self, message):
        """
        Handle the response from a captain asking for confirmation of beginning
        a goalie search for the specified game.
        """
        pacific = ZoneInfo('US/Pacific')
        datetime_str = f'{self.pending_goalie_search.scheduled_at.astimezone(pacific).strftime("%A at %I:%M %p")}'

        self.messages.append({"role": "system", "content": 'Reply in following format, replacing the text in the <> with your message: {"response": "<your response>"}'})
        self.messages.append({"role": "system", "content": f"tell the user that we will find a goalie for the game on {datetime_str}"})

        ai_msg = chat_gpt(self.messages, 'response', False)
        self.messages.append({"role": "assistant", "content": ai_msg})

        self.state = ConversationMessageTypes.chat
        return_goalie_search = self.pending_goalie_search
        self.pending_goalie_search = None

        return return_goalie_search

    def reach_out_to_goalie(self, goalie_search):
        """
        Reach out to a goalie to see if they are available to play.
        """
        if self.goal != Conversation.Goal.secure_goalie:
            self.set_goal(Conversation.Goal.secure_goalie)
        
        db = get_db()
        game = db.get_game_by_id(goalie_search.game_id)
        team = db.get_team_by_id(goalie_search.team_id)

        pacific = ZoneInfo('US/Pacific')
        instruction = f"""
        You need to reach out to {self.person_ref.name} to see if he is available to play goalie. Make sure your message includes the following:
        1. You are "Assistant Captain GPT".
        2. The team name is {team.name}.
        3. The game is on {game.scheduled_at.astimezone(pacific).strftime('%A, %B %d, %Y at %I:%M %p')}.
        4. The captain(s) are {', '.join(captain.name for captain in goalie_search.captains)} and they can be contacted for more information.
        Note: You may chat, remember to insist on a response indicating whether the goalie is available or not.
        """

        self.messages.append({"role": "system", "content": instruction})

        ai_msg = chat_gpt(self.messages, 'message', False)
        self.send_assistant_message(ai_msg)

    def respond_with_directive(self, directive):
        """
        Respond to the user with a directive on how to reply
        """
        self.messages.append({"role": "system", "content": directive})

        ai_msg = chat_gpt(self.messages, 'message', False)
        self.send_assistant_message(ai_msg)
    
    def __str__(self) -> str:
        pass

class Assistant:
    """
    The assistant is the main interface for the captain to interact with the
    system. It is responsible for managing the state of the conversation and
    the state of the goalie search.

    Game + team selection is not yet implemented so, for now, the team_id is
    hardcoded to the placeholder team, and game selection chooses the next
    game that does not have a confirmed goalie.

    In initial roll-out the expectation is that the captain will initiate a
    goalie search through the ui and initiate_goalie_search() which will specify
    the game and team, rather than the captain initiating the search through an
    ongoing conversation with the assistant captain.
    """
    def __init__(self):
        self.goalie_searches = {} # game_id -> GoalieSearch
        self.conversations = {} # phone_number -> Conversation

        if not os.path.exists(SAVE_DATA_DIR):
            os.makedirs(SAVE_DATA_DIR)
        if not os.path.exists(LOG_DATA_DIR):
            os.makedirs(LOG_DATA_DIR)
        print(f"Assistant initialized")

    @staticmethod
    def get_instance():
        assistant = current_app.config['assistant']
        return assistant

    def initiate_goalie_search(self, team_id, game_id):
        """
        Initiate a goalie search for the specified game.
        Returns True if the search was initiated successfully, False and an error message otherwise.
        """
        if game_id in self.goalie_searches:
            print(f"ERROR: Goalie search already in progress for game {game_id}")
            return True, None

        for goalie_search in self.goalie_searches.values():
            if goalie_search.team_id == team_id and goalie_search.state == GoalieSearch.State.unresolved:
                print(f"ERROR: There is already a search in progress for this team ({goalie_search.game_id}). One search per team at a time.")
                return False, f"ERROR: There is already a search in progress for this team ({goalie_search.game_id}). One search per team at a time."

        db = get_db()
        game = db.get_game_by_id(game_id)

        search = GoalieSearch(team_id, game_id, game.scheduled_at)
        self.goalie_searches[game_id] = search
        self._continue_goalie_search(search)
        return True, None

    def describe_goalie_searches_for_team(self, team_id):
        """
        Describe the goalie searches for a team
        """

        db = get_db()
        team = db.get_team_by_id(team_id)
        team_name = 'Unknown'
        if team is not None:
            team_name = team.name

        description = {}
        description['team_name'] = team_name
        description['team_id'] = team_id
        description['goalie_searches'] = []

        for game_id,search in self.goalie_searches.items():
            if search.team_id == team_id:

                search_details = {}

                pacific = ZoneInfo('US/Pacific')
                search_details["scheduled_at"] = search.scheduled_at.astimezone(pacific).strftime('%A, %B %d, %Y %I:%M:%S %p')
                search_details["game_id"] = game_id
                search_details["subs"] = []

                for person_ref,status in search.goalie_state.items():
                    sub = {}
                    sub["name"] = person_ref.name
                    sub["phone_number"] = phonenumbers.format_number(person_ref.phone_number, phonenumbers.PhoneNumberFormat.E164)
                    sub["status"] = status.name
                    sub["messages"] = []

                    convo = self._find_conversation(person_ref.phone_number)
                    
                    if convo is None:
                        continue

                    for message in convo.messages[1:]:
                        sub["messages"].append(message)
                    
                    search_details["subs"].append(sub)

                description["goalie_searches"].append(search_details)
        
        print(json5.dumps(description, indent=4))
        return description

    def receive_message(self, phone_number, message):
        """
        Receive a message from a user and respond accordingly
        """
        self._cleanup()

        parsed_phone_number = phonenumbers.parse(phone_number, "US")
        conversation = self._find_conversation(parsed_phone_number)
        if conversation is None:
            return

        retries = 0

        # Sometimes GPT will ignore a directive to classify a message, causing none of the
        # conversation logic to be executed. This is a hacky way to try to get around that.
        # GPT4 will probably be better, whenever that API is available.
        while retries < 2:
            message_type = conversation.receive_message(message)

            if message_type == ConversationMessageTypes.chat.name:
                conversation.handle_chat_message(message)
            elif message_type == ConversationMessageTypes.sub_goalie_request.name:
                conversation.handle_captain_goalie_request(message)
            elif message_type == ConfirmationMessageTypes.yes.name and conversation.state == ConversationMessageTypes.sub_goalie_request_confirming_which_game:
                goalie_search = conversation.handle_captain_goalie_request_confirming_game(message)

                if goalie_search is not None:
                    self._continue_goalie_search(goalie_search)
            elif message_type == GoalieConversationMessageTypes.confirmed.name:
                self._handle_goalie_confirmed(parsed_phone_number)
            elif message_type == GoalieConversationMessageTypes.declined.name:
                self._handle_goalie_declined(parsed_phone_number)
            else:
                print(f"ERROR: Unknown message type {message_type}. Retries {retries}")
                retries += 1
                continue
            
            # if we got here, the message was handled successfully
            break
        
        self._save_to_disk()

    ### PRIVATE METHODS ###

    def _notify_captains(self, captain_refs, message):
        """
        Notify the captains that a goalie has been found.
        """
        for captain_ref in captain_refs:
            if captain_ref.phone_number is None:
                continue

            captain_conversation = self._find_conversation(captain_ref.phone_number, captain_ref)
            captain_conversation.send_message(message)

    def _continue_goalie_search(self, goalie_search):
        """
        Continue a goalie search for the specified game.
        """
        if goalie_search.game_id not in self.goalie_searches:
            self.goalie_searches[goalie_search.game_id] = goalie_search

        next_candidate = goalie_search.next_goalie()
        if next_candidate is not None:
            goalie_conversation = self._find_conversation(next_candidate.phone_number, next_candidate)
            goalie_conversation.reach_out_to_goalie(goalie_search)
            self._notify_captains(goalie_search.captains, f"(system) Goalie {next_candidate.name} has been contacted")
        else:
            pacific = ZoneInfo('US/Pacific')
            self._notify_captains(goalie_search.captains, f"(system) Heads up! There are no goalies available for the game on {goalie_search.scheduled_at.astimezone(pacific).strftime('%A, %B %d, %Y %I:%M:%S %p')}. {len(goalie_search.goalie_state)} goalies were considered. You can add more goalies to the list on the team page.")
            print("ERROR: No next candidate for goalie search")

    def _find_goalie_search_for_number(self, phone_number):
        """
        Find the goalie search for the specified phone number.
        """
        for game_id,one_search in self.goalie_searches.items():
            for person_ref,status in one_search.goalie_state.items():
                if person_ref.phone_number == phone_number:
                    return one_search

        return None

    def _handle_goalie_confirmed(self, phone_number):
        """
        Handle a goalie confirming that they are available for a game.
        """
        goalie_conversation = self._find_conversation(phone_number)
        goalie_search = self._find_goalie_search_for_number(phone_number)
        
        if goalie_search is None:
            print(f"ERROR: No goalie search found for confirmed goalie phone number {phone_number}")
            return

        goalie_search.set_goalie_confirmed(goalie_conversation.person_ref)
        goalie_conversation.set_goal(Conversation.Goal.chat)

        goalie_conversation.respond_with_directive("tell him he is confirmed, thank him, tell him to notify the captain if there are any changes")
        pacific = ZoneInfo('US/Pacific')
        self._notify_captains(goalie_search.captains, f"(system) Goalie {goalie_conversation.person_ref.name} is confirmed for the game on {goalie_search.scheduled_at.astimezone(pacific).strftime('%A, %B %d, %Y %I:%M:%S %p')}")

    def _handle_goalie_declined(self, phone_number):
        """
        Handle a goalie declining to be a substitute goalie.
        """
        goalie_conversation = self._find_conversation(phone_number)
        goalie_search = self._find_goalie_search_for_number(phone_number)

        if goalie_search is None:
            print(f"ERROR: No goalie search found for confirmed goalie phone number {phone_number}")
            return

        goalie_search.set_goalie_declined(goalie_conversation.person_ref)
        goalie_conversation.set_goal(Conversation.Goal.chat)

        goalie_conversation.respond_with_directive("tell him thanks, we'll keep looking, and keep him in mind for future games")
        pacific = ZoneInfo('US/Pacific')
        self._notify_captains(goalie_search.captains, f"(system) Goalie {goalie_conversation.person_ref.name} has declined for the game on {goalie_search.scheduled_at.astimezone(pacific).strftime('%A, %B %d, %Y %I:%M:%S %p')}")

        self._continue_goalie_search(goalie_search) # move on to the next candidate

    def _find_conversation(self, phone_number, person_ref=None):
        """
        Find a conversation for a phone number. Person ref is passed when there is a new
        conversation with someone from the goalie list, who may not be in the database
        (and therefore may not have a name set)
        """
        assert(isinstance(phone_number, phonenumbers.PhoneNumber))
        hashable_phone_number = phonenumbers.format_number(phone_number, phonenumbers.PhoneNumberFormat.E164)

        if hashable_phone_number not in self.conversations:
            new_convo_person_ref = person_ref
            if new_convo_person_ref is None:
                user_id = get_user_id_for_phone_number(phone_number)

                if user_id is None: # receiving a message from someone who does not match an existing conversation and is not a registered user
                    return None

                new_convo_person_ref = PersonReference(get_user_id_for_phone_number(phone_number), None, phone_number)
    
            self.conversations[hashable_phone_number] = Conversation(new_convo_person_ref)
        return self.conversations[hashable_phone_number]

    def _cleanup(self):
        """
        Clean up old conversations and goalie searches
        """
        game_ids_to_delete = []
        for game_id,search in self.goalie_searches.items():
            if search.is_expired():
                game_ids_to_delete.append(game_id)

        for game_id in game_ids_to_delete:
            print(f"deleting goalie search for game {game_id}")
            del self.goalie_searches[game_id]

    def _save_to_disk(self):
        """
        Save ai state to a file as pickle
        """
        with open(SAVE_DATA_PATH, 'wb') as f:
            pickle.dump(self, f)

    @staticmethod
    def _read_from_disk():
        """
        Load ai state from a file as pickle
        """
        if os.path.exists(SAVE_DATA_PATH):
            with open(SAVE_DATA_PATH, 'rb') as f:
                assistant = pickle.load(f)
                return assistant
        print("ERROR: No save data found. Creating a new assistant.")
        return Assistant()
