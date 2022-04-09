import React, {useEffect, useRef, useState} from 'react';
import {
  Center,
  Checkbox,
  ChakraProvider,
  Container,
  Badge,
  Box,
  Button,
  GridItem,
  Flex,
  IconButton,
  Input,
  InputGroup,
  InputRightElement,
  Text,
  Link,
  List,
  ListIcon,
  ListItem,
  VStack,
  Code,
  Grid,
  Popover,
  PopoverArrow,
  PopoverCloseButton,
  PopoverContent,
  PopoverTrigger,
  theme,
  Select,
  SimpleGrid,
  Stack,
  StackDivider,
  Spacer,
  Wrap,
  WrapItem,
  useColorModeValue,
  useToast,
} from '@chakra-ui/react';
import {
  Table,
  Thead,
  Tbody,
  Tfoot,
  Tr,
  Th,
  Td,
  TableCaption,
} from "@chakra-ui/react"
import { ArrowForwardIcon, EditIcon } from '@chakra-ui/icons'
import { useNavigate, useParams } from "react-router-dom";
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { checkLogin, getData } from '../utils';
import TagManager from 'react-gtm-module'
import _ from "lodash";

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
  const [game, setGame] = useState([]);
  const [user, setUser] = useState(0);
  const [replies, setReplies] = useState([]);
  const [message, setMessage] = useState([]);
  const [userIsGoalie, setUserIsGoalie] = useState(false);
  const fetchedData = useRef(false);
  const responseReceived = useRef(false);
  const toast = useToast();

  const [userIsOnTeam, setUserIsOnTeam] = useState(true);
  const [isUserMembershipPending, setIsUserMembershipPending] = useState(false);

  // Popover control
  const [openPopover, setOpenPopover] = React.useState(0)
  const open = (user) => setOpenPopover(user);
  const close = () => setOpenPopover(0);


  function receiveReplyData(body) {
    let serverReplies = body;

    if (serverReplies['replies'] == undefined) {
      return;
    }

    // Sort replies
    serverReplies['replies'] = serverReplies['replies'].sort(function(a, b) {
      if (a['reply_id'] < b['reply_id']) {
        return -1;
      }
      if (a['reply_id'] > b['reply_id']) {
        return 1;
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
    console.log(serverReplies['user'])

    if (serverReplies['user']['reply']) {
      // If the user has replied, use that value of is_goalie, otherwise leave it alone
      // and the last set value from localStorage will remain populated
      setUserIsGoalie(_.get(serverReplies, 'user.reply.is_goalie', false));
    }
  }

  function receiveGameData(body) {
    responseReceived.current = true;
    setGame(body['games'][0])
    setUserIsOnTeam(body['games'][0]['is_user_on_team'])
    setIsUserMembershipPending(body['games'][0]['is_user_membership_pending'])
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

      getData(`/api/game/${game_id}/for-team/${team_id}`, receiveGameData);
      getData(`/api/game/reply/${game_id}/for-team/${team_id}`, receiveReplyData);
      fetchedData.current = true;
    }
  });

  function submitReply(event, user_id, response, new_msg, is_goalie) {

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
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status == 200) {
        TagManager.dataLayer({
          dataLayer: {
            event: 'game_reply'
          },
        });

        getData(`/api/game/reply/${game_id}/for-team/${team_id}`, receiveReplyData);
        return;
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
      submitReply(null, user.user_id, null, null, isGoalieChecked);
    }
  }

  const isUserCaptain = user['role'] == 'captain';

  let replyBadge = {};
  replyBadge['yes'] = <Badge colorScheme="green" my="0px">YES</Badge>;
  replyBadge['no'] = <Badge colorScheme="red" my="0px">NO</Badge>;
  replyBadge['maybe'] = <Badge colorScheme="blue" my="0px">Maybe</Badge>;
  replyBadge['goalie'] = <Badge colorScheme="yellow" mx={1} my="0px">G</Badge>;

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

  return (
    <ChakraProvider theme={theme}>
      <Header react_navigate={navigate} signed_in={user != {}}></Header>
      <Box textAlign="center" fontSize="xl" mt="50px" minH="500px">
          <SimpleGrid maxW="1200px" columns={2} minChildWidth='300px' spacing='40px' mx='auto'>
            <InfoBox>
              <Text>TIME: {game['scheduled_at']} (in {game['scheduled_how_soon']})</Text>
              <Text>RINK: {game['rink']}</Text>
              <Text>VS: {game['user_team']} {homeAwayLabel} vs {game['vs']}</Text>
              <Text>&nbsp;</Text>
              <Text>Players: {yesCount} {maybeCountStr}</Text>
              <Text>Goalie: {goalieLabel}</Text>
            </InfoBox>

          { userIsOnTeam && !isUserMembershipPending && responseReceived.current &&
            <Box textAlign="left" p="10px" mx="20px">
              <Text fontSize="0.8em" mb="8px">Update your status:</Text>
              <Button colorScheme='green' size='sm' mr="15px" onClick={(e) => submitReply(e, 0, 'yes', null, submitReply)}>
                YES
              </Button>
              <Button colorScheme='blue' size='sm' mr="15px" onClick={(e) => submitReply(e, 0, 'maybe', null, submitReply)}>
                Maybe
              </Button>
              <Button colorScheme='red' size='sm' onClick={(e) => submitReply(e, 0, 'no', null, submitReply)}>
                NO
              </Button>
              <Checkbox ml={8} mt='4px' colorScheme='green' isChecked={userIsGoalie} onChange={(e) => selectUserIsGoalie(e.target.checked)}>
                Goalie?
              </Checkbox>
              <form onSubmit={(e) => submitReply(e, 0, null, message)}>
                <InputGroup size='md' mt="28px">
                  <Input
                    pr='4.5rem'
                    type='text'
                    placeholder='Message'
                    onChange={(e) => setMessage(e.target.value)}
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
                  <Th w="25%">Player</Th>
                  <Th w="15%">Reply</Th>
                  <Th w="70%">Message</Th>
                </Tr>
              </Thead>
              <Tbody fontSize="0.8em">
                {
                  replies['replies'] && replies['replies'].map((reply) => (

                    <Tr key={reply.user_id}>
                      <Td py="6px">{reply.user_id == user['user_id'] ? <b>You ({user['role']})</b> : reply.name}</Td>
                      <Td>
                        {replyBadge[reply.response]}
                        { reply.is_goalie &&
                          replyBadge['goalie']
                        }
                      </Td>
                      <Td>
                        {
                          isUserCaptain &&
                          <Popover isOpen={reply.user_id == openPopover}>
                            <PopoverTrigger>
                              <IconButton size='xs' icon={<EditIcon />} onClick={() => open(reply.user_id)} my="5px" />
                            </PopoverTrigger>
                            <PopoverContent p={5} >
                                <PopoverArrow />
                                <PopoverCloseButton onClick={close} />

                                <Box textAlign="left" p="10px" mx="20px">
                                  <Text fontSize="0.8em" mb="8px">Update status for {reply.name}:</Text>
                                  <Button colorScheme='green' size='sm' mr="15px" onClick={(e) => submitReply(e, reply.user_id, 'yes', null)}>
                                    YES
                                  </Button>
                                  <Button colorScheme='blue' size='sm' mr="15px" onClick={(e) => submitReply(e, reply.user_id, 'maybe', null)}>
                                    Maybe
                                  </Button>
                                  <Button colorScheme='red' size='sm' onClick={(e) => submitReply(e, reply.user_id, 'no', null)}>
                                    NO
                                  </Button>
                                  <Checkbox ml={0} mt={6} colorScheme='green' isChecked={reply.is_goalie} onChange={(e) => submitReply(e, reply.user_id, null, null, e.target.checked)}>
                                    Goalie?
                                  </Checkbox>


                                  <form onSubmit={(e) => submitReply(e, reply.user_id, null, message)}>
                                    <InputGroup size='md' mt="28px">
                                      <Input
                                        pr='4.5rem'
                                        type='text'
                                        placeholder='Message'
                                        onChange={(e) => setMessage(e.target.value)}
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
                              </PopoverContent>
                            </Popover>
                        }
                        <span>&nbsp;&nbsp;</span>
                        {reply.message}
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
                  <Th w="25%">No Reply</Th>
                  <Th/>
                </Tr>
              </Thead>
              <Tbody fontSize="0.8em">
                {
                  replies['no_response'] && replies['no_response'].map((reply) => (

                    <Tr key={reply.user_id}>
                      <Td py="6px">{reply.user_id == user['user_id'] ? <b>You ({user['role']})</b> : reply.name}</Td>
                      <Td>
                        {
                          isUserCaptain &&
                          <Popover isOpen={reply.user_id == openPopover}>
                            <PopoverTrigger>
                              <IconButton size='xs' icon={<EditIcon />} onClick={() => open(reply.user_id)} my="5px" />
                            </PopoverTrigger>
                            <PopoverContent p={5} >
                                <PopoverArrow />
                                <PopoverCloseButton onClick={close} />

                                <Box textAlign="left" p="10px" mx="20px">
                                  <Text fontSize="0.8em" mb="8px">Update status for {reply.name}:</Text>
                                  <Button colorScheme='green' size='sm' mr="15px" onClick={(e) => submitReply(e, reply.user_id, 'yes', null)}>
                                    YES
                                  </Button>
                                  <Button colorScheme='blue' size='sm' mr="15px" onClick={(e) => submitReply(e, reply.user_id, 'maybe', null)}>
                                    Maybe
                                  </Button>
                                  <Button colorScheme='red' size='sm' onClick={(e) => submitReply(e, reply.user_id, 'no', null)}>
                                    NO
                                  </Button>

                                  <form onSubmit={(e) => submitReply(e, reply.user_id, null, message)}>
                                    <InputGroup size='md' mt="28px">
                                      <Input
                                        pr='4.5rem'
                                        type='text'
                                        placeholder='Message'
                                        onChange={(e) => setMessage(e.target.value)}
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
                              </PopoverContent>
                            </Popover>
                          }
                        <span>&nbsp;&nbsp;</span>
                        {replyBadge[reply.response]}
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
