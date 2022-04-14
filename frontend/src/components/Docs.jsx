import { CalendarIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import {
  Box,
  ChakraProvider,
  Link,
  List,
  ListItem,
  ListIcon,
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

    <Text fontSize='2xl' fontWeight='medium' color={headerColor}>Calendar</Text>
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
  <ListItem><b>Join Request</b> - When a new player requests to join a team, all captains on that team are sent a brief note.</ListItem>
  <ListItem><b>Role Change</b> - When your role is changed, you will receive a message. This is the message new players receive when their request is accepted.</ListItem>
  <ListItem><b>Removed from Team</b> - When (if?) you are removed from a team, you will receive a message.</ListItem>
</UnorderedList>
    <Text>
Other notifications are in the works and will follow (game-time-has-changed, new-games-added-to-schedule,
the-goalie-switched-his-reply-to-no, etc).
    </Text>
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
