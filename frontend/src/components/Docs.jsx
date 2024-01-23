import { CalendarIcon, DownloadIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import {
  Badge,
  Box,
  ChakraProvider,
  HStack,
  Link,
  ListItem,
  Tag,
  Text,
  theme,
  UnorderedList,
  useColorModeValue,
} from '@chakra-ui/react';
import React, {useEffect, useRef, useState} from 'react';
import { useNavigate, useParams } from "react-router-dom";
import TagManager from 'react-gtm-module'
import _ from "lodash";

import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { checkLogin, getAuthHeader, getData } from '../utils';

function DocsText(props: React.PropsWithChildren<MyProps>) {

  const headerColor = useColorModeValue('#637CB1', '#637CB1');
  const linkColor = useColorModeValue('blue.400', 'blue.300');

  return (
  <Box>
    <Text fontSize='2xl' fontWeight='medium' color={headerColor}>About Hockey Reply</Text>
    <Text>
Hockey Reply is a site for managing the roster of upcoming games. It was built to make life easier
in the adult league at Sharks Ice San Jose. This site obviously shares similarities with its
predecessors that we were bummed-out to see shut down. The hope is that by making this web app
open source, the community can pick it up and keep it going whenever its builder moves on to a new hobby.
    </Text>
    <br/>


    <Text fontSize='2xl' fontWeight='medium' color={headerColor}>Getting Started</Text>
    <Text>
First create an account. Once you are signed in, select <Tag color='grey.300'>Join a Team</Tag> on
the Home page to request to join a team. If you are the first player to join, you will automatically
be added and assigned as captain. Otherwise, you will need to wait for your request to be accepted
before you can go further.
    </Text>
    <br/>
    <Text fontSize='lg' fontWeight='medium' color={headerColor}>Inviting Teammates</Text>
    <Text>
To invite other team members to join, click the <ExternalLinkIcon mb='4px'/> button to
send them the link to your team. Once they create an account, they'll be taken straight to a
button to join your team.
    </Text>
    <br/>
    <Text fontSize='lg' fontWeight='medium' color={headerColor}>Contact Info + USA Hockey Number</Text>
    <Text>
Update your profile with your cell phone and USA Hockey numbers so that they can be available to your team.
You can access your teammates' contact info from the team page. Tap any teammate and a pop-up will appear
that will let you send them an SMS, email, or copy their USA hockey number.
    </Text>
    <br/>
    <Text fontSize='lg' fontWeight='medium' color={headerColor}>Calendar</Text>
    <Text>
Once you have joined a team. You can download the calendar by tapping the <CalendarIcon mx='2px' mb='4px'/> button
next to your team on the home page. An .ics file will be downloaded that you can import into your
calendar app.
    </Text>
    <Text mt={2}>
You can also have new games automatically added to your calendar by
subscribing to that link with your calendar app (right-click and select <i>Copy Link Address</i>).
Check out these links to learn more about how to subscribe on your <Link color={linkColor} href='https://support.apple.com/en-us/HT202361'>Mac, iPhone,</Link> or <Link color={linkColor} href='https://support.google.com/calendar/answer/37100?hl=en&co=GENIE.Platform%3DDesktop'>Google calendar</Link>.
    </Text>
    <br/>


    <Text fontSize='2xl' fontWeight='medium' color={headerColor} my={2}>Team Management</Text>
    <Text>
  There are 3 roles available for players on a team. Roles are managed from the team page. On the team page the captains may (re)assign player roles or remove players from the team.
    </Text>
    <UnorderedList ml={10} my={2}>
      <ListItem><b>Captain</b> - Has the ability to remove/confirm players, adjust player roles, and update player replies for games. The first person to join a team becomes the captain. Multiple players can share the captain role. </ListItem>
      <ListItem><b>Full</b> - Indicates the player has paid for the full season. Player can only modify their own replies.</ListItem>
      <ListItem><b>Half</b> - Indicates the player has paid for half of the season. Player can only modify their own replies.</ListItem>
      <ListItem><b>Sub</b> - Indicates the player has is available to play if the team is short handed.</ListItem>
      <ListItem><b>[blank]</b> - Players who have requested to join the team, show up with a blank role. These players cannot view the team roster or game replies until they have been added to the team by a captain, by assigning them one of the player roles (captain/full/half/sub).</ListItem>
    </UnorderedList>
    <Text fontSize='lg' fontWeight='medium' color={headerColor}>Unrostered Subs</Text>
    <Text>
Unrostered subs can be added on a per game basis. This means you can have a person represented in the game
replies, player counts, and goalie status without requiring them to create an account and join the team.
To add an unrostered sub, simply change the status of the <i>"Anonymous Sub"</i> player listed in the NO REPLY
section of the game page. Multiple anonymous subs can be added per game, and they can be marked as goalie.
Editable by captains only.
    </Text>
    <br/>
    <Text fontSize='lg' fontWeight='medium' color={headerColor}>Sign-in Sheets</Text>
    <Text>
You can download a sign-in sheet for your team that has been pre-filled out with registered players and their
jersey numbers. Go to the team page and tap the <DownloadIcon mb='4px'/> to display the sign-in sheet PDF.
Player jersey numbers can be updated on the same page. Players can update their own numbers and captains
can update the numbers for anyone on the team.
    </Text>
    <br/>


    <Text fontSize='2xl' fontWeight='medium' color={headerColor}>Notifications</Text>
    <Text>
Notifications are sent over email for notable events:
    </Text>
<UnorderedList ml={10} my={2}>
  <ListItem><b>Game Coming Soon</b> - 
Upcoming game notifications are sent via email and you can easily add your reply by tapping one of the
&nbsp;<Tag colorScheme="green">Yes</Tag>&nbsp;&nbsp;<Tag colorScheme="red">No</Tag>&nbsp;or&nbsp;<Tag colorScheme="blue">Maybe</Tag>&nbsp;options
from within the message.
  </ListItem>
  <ListItem><b>Game Time Changed</b> - Every once and awhile there is a schedule change. You'll receive a note when it happens.</ListItem>
  <ListItem><b>Join Request</b> - When a new player requests to join a team, all captains on that team are sent a brief note.</ListItem>
  <ListItem><b>Role Change</b> - When your role is changed, you will receive a message. This is the message new players receive when their request is accepted.</ListItem>
  <ListItem><b>Game Reply Changed</b> - When your reply is changed by someone else (a captain), you'll be notified.</ListItem>
  <ListItem><b>Removed from Team</b> - When (if?) you are removed from a team, you will receive a message.</ListItem>
</UnorderedList>
    <br/>

    <HStack>
      <Text fontSize='2xl' fontWeight='medium' color={headerColor}>Assistant Captain GPT</Text>
      <Badge variant='outline' colorScheme="gray" mt="0px" mr='auto'>BETA</Badge>
    </HStack>
    <Text>
Assistant Captain GPT is a chat-based assistant that can help you manage your team. It currently supports
helping team captains find substitute goalies for upcoming games. It is considered BETA while it gets some
real world testing to identify and work out any issues.
    </Text>
    <br/>
    <Text>
Interactions with the assistant captain happen both over SMS and in the UI on the site. To use the assistant:
    </Text>
<UnorderedList ml={10} my={2}>
  <ListItem>
    <b>Build a Goalie List</b> - There is a new section on the team page for goalies (visible to captains only).
    Add the list of goalies you use for your team. Make sure they are in priority order. It can include both rostered and unrostered players.
    Your primary goalie should be the first person listed. This is the list and the order that the assistant captain will use to find a goalie, when requested.
  </ListItem>
  <ListItem>
    <b>Find Goalie</b> - Below the goalie status on the page for a specific game, there is a new <Tag color='grey.300'>Find Goalie</Tag> button
    (visible to captains only and hidden once a goalie is confirmed). Tapping this button will initiate a goalie search.
  </ListItem>
  <ListItem><b>
    Goalie Conversations</b> - After a goalie search has been initiated, below the goalie status there will be a <Tag color='grey.300'>Goalie Conversations</Tag> button.
    This button will present a dialog displaying all of the message threads between the assistant captain and each of the goalies on your list, as well as their
    status: <Tag colorScheme='gray'>Unknown</Tag>, <Tag colorScheme='green'>Accepted</Tag>, <Tag colorScheme='red'>Declined</Tag>, <Tag colorScheme='blue'>Needs More Time</Tag>
  </ListItem>
  <ListItem>
    <b>Notifications</b> - Captains will receive SMS updates on each step of the goalie search process: when each sub is contacted and when they accept/decline.
  </ListItem>
</UnorderedList>
    <br/>

    <Text fontSize='2xl' fontWeight='medium' color={headerColor}>Contributing</Text>
    <Text>
Hockey Reply is free and open source. You can find <Link color={linkColor} href='https://github.com/jesseboettcher/hockey-reply'>the code on GitHub</Link>.
    </Text>
    <br/>
    <br/>
    <Text mb={2} textAlign='center' fontSize='xs'>Tap the little NES ice hockey guy at the bottom to send feedback. Thanks!</Text>
  </Box>
  )
}

export default function Docs() {

  let navigate = useNavigate();
  const fetchedData = useRef(false);
  const [user, setUser] = useState({});

  useEffect(() => {
    if (!fetchedData.current) {
      TagManager.dataLayer({
        dataLayer: {
          event: 'pageview',
          pagePath: window.location.pathname,
          pageTitle: 'Home',
        },
      });
      checkLogin(null).then(result => { setUser(result) });

      fetchedData.current = true;
    }
  });

  return (
    <ChakraProvider theme={theme}>
      <Header react_navigate={navigate} signed_in={_.has(user, 'user_id', false)}></Header>
      <Box minH='300px' mt={10} mx={{ base:'20px', md:'50px'}}>
        <DocsText/>
      </Box>
      <Footer></Footer>
    </ChakraProvider>
  );
}
