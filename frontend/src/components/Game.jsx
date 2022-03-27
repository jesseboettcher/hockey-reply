import React, {useEffect, useRef, useState} from 'react';
import {
  Center,
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
import { ColorModeSwitcher } from '../components/ColorModeSwitcher';
import { checkLogin } from '../utils';

function getData(url, setFn) {
    fetch(url, {credentials: 'include'})
    .then(r =>  r.json().then(data => ({status: r.status, body: data})))
      .then(obj => {
          return setFn(obj.body)
      });
}

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
  const fetchedData = useRef(false);
  const toast = useToast();

  // Popover control
  const [openPopover, setOpenPopover] = React.useState(0)
  const open = (user) => setOpenPopover(user);
  const close = () => setOpenPopover(0);


  function receiveReplyData(body) {
    let serverReplies = body;

    serverReplies['replies'] = serverReplies['replies'].sort(function(a, b) {
      if (a['reply_id'] < b['reply_id']) {
        return -1;
      }
      if (a['reply_id'] > b['reply_id']) {
        return 1;
      }
      return 0;
    });

    setReplies(serverReplies)
    setUser(serverReplies['user'])
  }
  function receiveGameData(body) {
    setGame(body['games'][0])
  }

  useEffect(() => {
    if (!fetchedData.current) {
      checkLogin(navigate);

      getData(`/api/game/${game_id}/for-team/${team_id}`, receiveGameData);
      getData(`/api/game/reply/${game_id}/for-team/${team_id}`, receiveReplyData);
      fetchedData.current = true;
    }
  });

  function submitReply(event, user_id, response, new_msg) {

    event.preventDefault();
    close();

    let data = {
      game_id: game_id,
      team_id: team_id,
      response: response,
      message: new_msg,
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
        getData(`/api/game/reply/${game_id}/for-team/${team_id}`, receiveReplyData);
        return;
      }
    });
  };

  const isUserCaptain = user['role'] == 'captain';

  let replyBadge = {};
  replyBadge['yes'] = <Badge colorScheme="green" my="0px">YES</Badge>;
  replyBadge['no'] = <Badge colorScheme="red" my="0px">NO</Badge>;
  replyBadge['maybe'] = <Badge colorScheme="blue" my="0px">Maybe</Badge>;

  let yesCount = 0;
  let maybeCount = 0;

  if (replies['replies']) {
    replies['replies'].forEach(element => {
      yesCount += element['response'] === 'yes';
      maybeCount += element['response'] === 'maybe';
    });
  }
  let maybeCountStr = ''
  if (maybeCount) {
    maybeCountStr = `(+${maybeCount} maybe)`
  }

  return (
    <ChakraProvider theme={theme}>
      <Box textAlign="center" fontSize="xl" mt="50px">
          <SimpleGrid maxW="1200px" columns={2} minChildWidth='300px' spacing='40px' mx='auto'>
            <InfoBox>
              <Text>TIME: {game['scheduled_at']}</Text>
              <Text>RINK: {game['rink']}</Text>
              <Text>VS: {game['away_team_name']}</Text>
              <Text>&nbsp;</Text>
              <Text>Players: {yesCount} {maybeCountStr}</Text>
              <Text>Goalie: Yes</Text>
            </InfoBox>
            <Box textAlign="left" p="10px" mx="20px">
              <Text fontSize="0.8em" mb="8px">Update your status:</Text>
              <Button colorScheme='green' size='sm' mr="15px" onClick={(e) => submitReply(e, 0, 'yes', null)}>
                YES
              </Button>
              <Button colorScheme='blue' size='sm' mr="15px" onClick={(e) => submitReply(e, 0, 'maybe', null)}>
                Maybe
              </Button>
              <Button colorScheme='red' size='sm' onClick={(e) => submitReply(e, 0, 'no', null)}>
                NO
              </Button>
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

          </SimpleGrid>

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
                        {
                          isUserCaptain &&
                          <Popover isOpen={reply.user_id == openPopover}>
                            <PopoverTrigger>
                              <IconButton size='sm' icon={<EditIcon />} onClick={() => open(reply.user_id)} my="5px" />
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
                      <Td>{reply.message}</Td>
                    </Tr>

                 ))
                }
              </Tbody>
            </Table>
          </Center>

          <Center>
            <Table size="sml" maxWidth="1200px" my="50px" mx="20px">
              <Thead fontSize="0.6em">
                <Tr>
                  <Th w="25%">No Reply</Th>
                </Tr>
              </Thead>
              <Tbody fontSize="0.8em">
                {
                  replies['no_response'] && replies['no_response'].map((reply) => (

                    <Tr key={reply.user_id}>
                      <Td py="6px">{reply.name}</Td>
                    </Tr>

                 ))
                }
              </Tbody>
            </Table>
          </Center>
          <ColorModeSwitcher justifySelf="flex-end" />

      </Box>
    </ChakraProvider>
  );
}

export default Game;
