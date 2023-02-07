import dayjs from 'dayjs';
import { ArrowForwardIcon } from '@chakra-ui/icons'
import {
  Center,
  Checkbox,
  ChakraProvider,
  Container,
  Badge,
  Box,
  Button,
  extendTheme,
  IconButton,
  Input,
  InputGroup,
  InputRightElement,
  Text,
  Link,
  List,
  ListIcon,
  ListItem,
  Popover,
  PopoverArrow,
  PopoverCloseButton,
  PopoverContent,
  PopoverTrigger,
  Select,
  SimpleGrid,
  Stack,
  Table,
  Thead,
  theme,
  Tbody,
  Tr,
  Th,
  Td,
  useColorModeValue,
  useToast,
  VStack,
} from '@chakra-ui/react';
import React, {useEffect, useRef, useState} from 'react';
import TagManager from 'react-gtm-module'
import { useNavigate, useParams } from "react-router-dom";
import _ from "lodash";

import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { checkLogin, getAuthHeader, getData, getPageData } from '../utils';
import { ReplyBox } from '../components/ReplyBox';

const themeWithBadgeCustomization = extendTheme({
  colors: {
    gold: {
      100: "#FFF1B9",
      200: "#FFEDA9",
      800: "#6E5E01",
    },
  },
})

function InfoBox(props: React.PropsWithChildren<MyProps>) {
  const infoBoxColor = useColorModeValue('#F0F8FE', '#303841')
  const infoBoxBorderColor = useColorModeValue('#DDE5EB', '#495563')

  return (
    <Box textAlign="left"
         fontSize="0.8em"
         bg={infoBoxColor}
         borderColor={infoBoxBorderColor}
         borderWidth='1px'
         borderRadius='10px'
         p="10px"
         mx="20px">
         {props.children}
    </Box>
    )
}

function Game() {

  let { game_id, team_id } = useParams();
  let navigate = useNavigate();

  // Popover control
  const [openPopover, setOpenPopover] = React.useState(0)
  const open = (user) => setOpenPopover(user);
  const close = () => setOpenPopover(0);

  // Fetch data
  const [game, setGame] = useState([]);
  const [user, setUser] = useState(0);
  const [replies, setReplies] = useState([]);
  const [message, setMessage] = useState([]);
  const [userIsGoalie, setUserIsGoalie] = useState(false);
  const fetchedData = useRef(false);
  const [lastRefresh, setLastRefresh] = React.useState(dayjs())
  const [pageError, setPageError] = React.useState(null)
  const responseReceived = useRef(false);
  const toast = useToast();

  const [userIsOnTeam, setUserIsOnTeam] = useState(true);
  const [isUserMembershipPending, setIsUserMembershipPending] = useState(false);

  const loadPageData = async () => {
      const loadDataResult = await getPageData([{url: `/api/game/${game_id}/for-team/${team_id}`, handler: receiveGameData},
                                                {url: `/api/game/reply/${game_id}/for-team/${team_id}`, handler: receiveReplyData}],
                                               setLastRefresh);
      if (!loadDataResult) {
        setPageError('Uh, oh. Could not get the latest data.');
      }
  }

  useEffect(() => {
    if (!fetchedData.current) {
      TagManager.dataLayer({
        dataLayer: {
          event: 'pageview',
          pagePath: window.location.pathname,
          pageTitle: 'Game',
        },
      });

      checkLogin(navigate);

      if (window.localStorage.getItem('is_goalie') != null) {
        setUserIsGoalie(window.localStorage.getItem('is_goalie') === true.toString());
      }

      loadPageData();
      fetchedData.current = true;
    }
  });

  function receiveReplyData(body) {
    let serverReplies = body;

    if (serverReplies['replies'] == undefined) {
      return;
    }

    // Sort replies
    serverReplies['replies'] = serverReplies['replies'].sort(function(a, b) {

      // Push no replies all the way to the bottom so the order is yes -> maybe -> no
      if (a['response'] == 'no' && b['response'] != 'no') {
        return 1;
      }
      if (b['response'] == 'no' && a['response'] != 'no') {
        return -1;
      }

      if (a['response'] > b['response']) {
        return -1;
      }
      if (a['response'] < b['response']) {
        return 1;
      }

      if (a['name'].toLowerCase() > b['name'].toLowerCase()) {
        return 1;
      }
      if (a['name'].toLowerCase() < b['name'].toLowerCase()) {
        return -1;
      }
      return 0;
    });

    // Sort not replied (put logged in user on top)
    serverReplies['no_response'] = serverReplies['no_response'].sort(function(a, b) {
      if (a['user_id'] == serverReplies['user']['user_id']) {
        return -1;
      }
      if (b['user_id'] == serverReplies['user']['user_id']) {
        return 1;
      }
      return a['name'].localeCompare(b['name']);
    });

    let userReply = serverReplies['replies'].find(item => item.user_id == serverReplies['user']['user_id']);
    serverReplies.user.reply = userReply

    setReplies(serverReplies);
    setUser(serverReplies['user']);

    if (serverReplies['user']['reply']) {
      // If the user has replied, use that value of is_goalie, otherwise leave it alone
      // and the last set value from localStorage will remain populated
      setUserIsGoalie(_.get(serverReplies, 'user.reply.is_goalie', false));
    }
  }

  function receiveGameData(body) {
    responseReceived.current = true;

    if (_.has(body, 'games')) {
      setGame(body['games'][0])
      setUserIsOnTeam(body['games'][0]['is_user_on_team'])
      setIsUserMembershipPending(body['games'][0]['is_user_membership_pending'])
    }
  }

  function submitReply(event, user_id, team_id, game_id, response, new_msg, is_goalie) {

    if (new_msg) {
      setMessage('')
    }

    if (event) {
      event.preventDefault();
    }
    close();

    let data = {
      game_id: game_id,
      team_id: team_id,
      response: response,
      message: new_msg,
      is_goalie: is_goalie
    };
    if (user_id != 0) {
      data.user_id = user_id;
    }

    fetch(`/api/game/reply/${game_id}/for-team/${team_id}`, {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json', 'Authorization': getAuthHeader()},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status == 200) {
        TagManager.dataLayer({
          dataLayer: {
            event: 'game_reply'
          },
        });
        setPageError(null);

        getData(`/api/game/reply/${game_id}/for-team/${team_id}`, receiveReplyData, true);
        return;
      }
      else {
        setPageError('Uh, oh. Could not send your reponse.');
      }
    });
  };

  function selectUserIsGoalie(isGoalieChecked) {
    setUserIsGoalie(isGoalieChecked);
    window.localStorage.setItem('is_goalie', isGoalieChecked.toString());

    let userReply = replies.replies.find(item => item.user_id == user.user_id);

    // Only submit the goalie flag, if there is already a response, so an empty response
    // is not created
    if (_.get(userReply, 'response', '') != '') {
      submitReply(null, user.user_id, team_id, game_id, null, null, isGoalieChecked);
    }
  }

  // Precompute some content to include in the rendering
  const isUserCaptain = user['role'] == 'captain';

  let replyBadge = {};
  replyBadge['goalie'] = <Badge colorScheme="gold" textAlign='center' width='80px' mx={2} my="0px">Goalie</Badge>;

  let yesCount = 0;
  let maybeCount = 0;
  let haveGoalie = false;

  if (replies['replies']) {
    replies['replies'].forEach(element => {
      yesCount += element['response'] === 'yes' && element['is_goalie'] == false;
      maybeCount += element['response'] === 'maybe' && element['is_goalie'] == false;

      if (element['is_goalie'] && element['response'] === 'yes') {
        haveGoalie = true;
      }
    });
  }
  let maybeCountStr = '';
  if (maybeCount) {
    maybeCountStr = `(+${maybeCount} maybe)`;
  }

  let homeAwayLabel = '(home)';
  if (game.user_team_id == game.away_team_id) {
    homeAwayLabel = '(away)';
  }

  let goalieLabel = <span>&#x1f937;</span>;
  if (haveGoalie) {
    goalieLabel = <span>&#x1F44D;</span>;
  }

  let no_response_users = [];
  if (replies['no_response']) {
    no_response_users = no_response_users.concat(replies['no_response'])
  }

  let next_anonymous_sub_id = undefined;
  if (replies['replies']) {
    next_anonymous_sub_id = -1 * (replies['replies'].length + 1);
    no_response_users.push({user_id:next_anonymous_sub_id, name:'Anonymous Sub'});
  }

  return (
    <ChakraProvider theme={themeWithBadgeCustomization}>
      <Header lastRefresh={lastRefresh} pageError={pageError}/>
      <Box textAlign="center" fontSize="xl" mt="50px" minH="500px">
          <SimpleGrid maxW="1200px" columns={2} minChildWidth='300px' spacing='40px' mx='auto'>
          { responseReceived.current &&
            <InfoBox>
              <Text>TIME: {game['scheduled_at']} ({game['scheduled_how_soon']})</Text>
              <Text>RINK: {game['rink']}</Text>
              <Text>VS: {game['user_team']} {homeAwayLabel} vs {game['vs']}</Text>
              <Text>Locker Room: {game['locker_room']}</Text>
              <Text>&nbsp;</Text>
              <Text>Players: {yesCount} {maybeCountStr}</Text>
              <Text>Goalie: {goalieLabel}</Text>
            </InfoBox>
          }
          { userIsOnTeam && !isUserMembershipPending && responseReceived.current &&
            <Box textAlign="left" p="10px" mx="20px">
              <Text fontSize="0.8em" mb="8px">Update your status:</Text>
              <Button colorScheme='green' size='sm' mr="15px" onClick={(e) => submitReply(e, user.user_id, team_id, game_id, 'yes', null, userIsGoalie)}>
                YES
              </Button>
              <Button colorScheme='blue' size='sm' mr="15px" onClick={(e) => submitReply(e, user.user_id, team_id, game_id, 'maybe', null, userIsGoalie)}>
                Maybe
              </Button>
              <Button colorScheme='red' size='sm' onClick={(e) => submitReply(e, user.user_id, team_id, game_id, 'no', null, userIsGoalie)}>
                NO
              </Button>
              <Checkbox ml={8} mt='4px' colorScheme='green' isChecked={userIsGoalie} onChange={(e) => selectUserIsGoalie(e.target.checked)}>
                Goalie?
              </Checkbox>
              <form onSubmit={(e) => submitReply(e, user.user_id, team_id, game_id, null, message)}>
                <InputGroup size='md' mt="28px">
                  <Input
                    pr='4.5rem'
                    type='text'
                    placeholder='Message'
                    onChange={(e) => setMessage(e.target.value)}
                    value={message}
                    key="main"
                  />
                  <InputRightElement width='4.5rem'>
                    <Button h='1.75rem' size='sm' type="submit">
                      Send
                    </Button>
                  </InputRightElement>
                </InputGroup>
              </form>
            </Box>
          }
          </SimpleGrid>

          { isUserMembershipPending && responseReceived.current &&
            <Box mx={10} mt={20} mb={40}>
              <Text fontSize="lg">Your request to join <b>{game['user_team']}</b> has not been accepted yet.</Text>
            </Box>
          }
          { !userIsOnTeam && !isUserMembershipPending &&
            <Box mx={10} mt={20} mb={40}>
              <Text fontSize="lg">You are not on this team.</Text>
            </Box>
          }

          { userIsOnTeam && !isUserMembershipPending && responseReceived.current &&
          <Center>
            <Table size="sml" maxWidth="1200px" mt="50px" mx="20px">
              <Thead fontSize="0.6em">
                <Tr>
                  <Th w='115px'>Reply</Th>
                  <Th >Player</Th>
                </Tr>
              </Thead>
              <Tbody fontSize="0.8em">
                {
                  replies['replies'] && replies['replies'].map((reply) => (

                    <Tr key={reply.user_id}>
                      <Td>
                        <ReplyBox
                          isOpen={reply.user_id == openPopover}
                          openHandler={() => open(reply.user_id)}
                          closeHandler={close}
                          user_id={reply.user_id}
                          team_id={team_id}
                          game_id={game_id}
                          user_reply={reply.response}
                          goalie
                          is_goalie={reply.is_goalie}
                          name={reply.name}
                          submitHandler={submitReply}
                          showMessageBox={true}
                          setMessage={setMessage}
                          editable={isUserCaptain}
                        />
                        { reply.is_goalie &&
                          replyBadge['goalie']
                        }
                      </Td>
                      <Td py="6px">{reply.user_id == user['user_id'] ? <b>You ({user['role']})</b> : reply.name}
                        <Stack>
                          { reply.message &&
                          <Text color='gray.500'>"{reply.message}"</Text>
                          }
                        </Stack>
                      </Td>
                    </Tr>

                 ))
                }
              </Tbody>
            </Table>
          </Center>
          }
          { userIsOnTeam && !isUserMembershipPending && responseReceived.current &&
          <Center>
            <Table size="sml" maxWidth="1200px" my="50px" mx="20px">
              <Thead fontSize="0.6em">
                <Tr>
                  <Th w='115px'>No Reply</Th>
                  <Th ></Th>
                </Tr>
              </Thead>
              <Tbody fontSize="0.8em">
                {
                  no_response_users.map((reply) => (

                    <Tr key={reply.user_id}>
                      <Td py="6px">
                          <ReplyBox
                            isOpen={reply.user_id == openPopover}
                            openHandler={() => open(reply.user_id)}
                            closeHandler={close}
                            user_id={reply.user_id}
                            team_id={team_id}
                            game_id={game_id}
                            name={reply.name}
                            user_reply=''
                            submitHandler={submitReply}
                            editable={isUserCaptain}
                          />
                      </Td>
                      <Td py="6px">
                        {reply.user_id == user['user_id'] ? <b>You ({user['role']})</b> : reply.name}
                      </Td>
                    </Tr>

                 ))
                }
              </Tbody>
            </Table>
          </Center>
        }
      </Box>
      <Footer></Footer>
    </ChakraProvider>
  );
}

export default Game;
