import {
  Box,
  Center,
  ChakraProvider,
  List,
  ListItem,
  ListIcon,
  OrderedList,
  Tag,
  Text,
  theme,
  UnorderedList,
  useColorModeValue,
} from '@chakra-ui/react';
import { ExternalLinkIcon } from '@chakra-ui/icons';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import React, {useEffect, useRef, useState} from 'react';
import { useNavigate, useParams } from "react-router-dom";
import { checkLogin, getAuthHeader, getData } from '../utils';
import TagManager from 'react-gtm-module'
import _ from "lodash";

function DocsText(props: React.PropsWithChildren<MyProps>) {

  const headerColor = useColorModeValue('#637CB1', '#637CB1');

  return (
  <Box>
    <Text fontSize='2xl' fontWeight='medium' color={headerColor}>About Hockey Reply</Text>
    <Text>
Hockey Reply is a site for managing the roster of upcoming games. It was built only to make life in
the Sharks Ice at San Jose Adult League easier to manage. This site obviously shares similarities
with its predecessors that we were bummed out to see shut down. The hope is that by making this web app
open source (coming soon), the community can pick it up and keep it going whenever its builder moves on to a new hobby.
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
Upcoming game notifications are sent via email and you can easily add your reply by tapping one of the
&nbsp;<Tag colorScheme="green">Yes</Tag>&nbsp;&nbsp;<Tag colorScheme="red">No</Tag>&nbsp;or&nbsp;<Tag colorScheme="blue">Maybe</Tag>&nbsp;options
from within the message.
    </Text>
    <br/>
    <Text>
Other notifications are in the works and will follow (player-requested-to-join team, you-were-accepted-to-team,
the-goalie-switched-his-reply-to-no, etc).
    </Text>
    <br/>

    <Text fontSize='2xl' fontWeight='medium' color={headerColor}>Contributing</Text>
    <Text>
GitHub repo coming soon.
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