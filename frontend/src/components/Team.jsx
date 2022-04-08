import React, {useEffect, useRef, useState} from 'react';
import {
  AlertDialog,
  AlertDialogOverlay,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogBody,
  AlertDialogFooter,
  ChakraProvider,
  Center,
  Divider,
  Box,
  Button,
  Icon,
  IconButton,
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
  VStack,
  Code,
  Grid,
  theme,
  Select,
  Stack,
  useDisclosure,
  useToast
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
import { ArrowForwardIcon, ChevronDownIcon, EmailIcon, ChatIcon } from '@chakra-ui/icons'
import { useNavigate, useParams } from "react-router-dom";
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { checkLogin, getData } from '../utils';
import TagManager from 'react-gtm-module'

function Team() {

  let { team_name_or_id } = useParams();
  let navigate = useNavigate();
  const [userIsOnTeam, setUserIsOnTeam] = useState(false);
  const [teamId, setTeamId] = useState(0);
  const [teamName, setTeamName] = useState('this team');
  const [players, setPlayers] = useState([]);
  const [user, setUser] = useState(0);
  const fetchedData = useRef(false);
  const responseReceived = useRef(false);
  const toast = useToast();

  const isUserCaptain = user['role'] == 'captain';
  const isUserMembershipPending = user['role'] == '';

  // Remove Player alert
  const [playerPendingRemoval, setPlayerPendingRemoval] = React.useState({})
  const { isAlertOpen, onAlertOpen, onAlertClose } = useDisclosure()
  const [openAlert, setOpenAlert] = React.useState(false)
  const cancelAlertRef = React.useRef()

  const { isOpen, onOpen, onClose } = useDisclosure()
  const cancelRef = React.useRef()

  function cancelRemovePlayer() {

    // Restore current role in selection
    let player_list = players;

    for (var i = 0; i < player_list.length;i++) {
      if (player_list[i].user_id == playerPendingRemoval.user_id) {
        player_list[i].role = player_list[i].save_role;
      }
    }
    setPlayers(player_list);

    setPlayerPendingRemoval({})
    onClose();
  }

  function confirmRemovePlayer() {
    removePlayer(playerPendingRemoval['user_id'])
    onClose();
  }

  function roleSelectionChange(player, role) {

    if (role === 'remove') {
      let player_list = players;

      for (var i = 0; i < player_list.length;i++) {
        if (player_list[i].user_id == player.user_id) {
          player_list[i].save_role = player_list[i].role;
          player_list[i].role = 'remove';
        }
      }
      setPlayers(player_list);

      setPlayerPendingRemoval(player);
      onOpen();
      return;
    }

    let data = {
      team_id: teamId,
      user_id: player['user_id'],
      role: role
    };

    fetch(`/api/player-role`, {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status == 200) {
        TagManager.dataLayer({
          dataLayer: {
            event: 'player_role_change',
            pagePath: window.location.pathname,
          },
        });

        // TODO smarter refresh
        window.location.reload();
        return;
      }
    });
  };

  function removePlayer(user_id) {

    let data = {
      team_id: teamId,
      user_id: user_id
    };

    fetch(`/api/remove-player`, {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status == 200) {

        var filtered = players.filter(function(value, index, arr){ 
            return value['user_id'] != user_id;
        });
        setPlayers(filtered);

        // TODO smarter refresh
        window.location.reload();
      }
    });
  };

  function joinTeam() {
    let data = {
      team_name: teamName,
      user_id: user['user_id'],
    };

    fetch(`/api/join-team`, {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status == 200) {
        // TODO smarter refresh
        window.location.reload(false);
        return;
      }
    });
    onClose();
  };


  function receivePlayerData(body) {

    let serverReplies = body;
    responseReceived.current = true;

    if (serverReplies['result'] && serverReplies['result'] == 'USER_NOT_ON_TEAM') {
      setUserIsOnTeam(false);
      setTeamName(body['team_name']);
      setTeamId(body['team_id']);
      return;
    }

    // Sort not replied (put logged in user on top)
    serverReplies['players'] = serverReplies['players'].sort(function(a, b) {
      if (a['user_id'] == serverReplies['user']['user_id']) {
        return -1;
      }
      if (b['user_id'] == serverReplies['user']['user_id']) {
        return 1;
      }
      return a['name'].localeCompare(b['name']);
    });

    setUserIsOnTeam(true);
    setPlayers(body['players'])
    setUser(body['user'])
    setTeamId(body['team_id']);
    setTeamName(body['team_name'])
  }

  useEffect(() => {

    if (!fetchedData.current) {
      checkLogin(navigate).then( data => {
        setUser({ user_id: data['user_id' ]})
      });

      TagManager.dataLayer({
        dataLayer: {
          event: 'pageview',
          pagePath: window.location.pathname,
          pageTitle: 'Game',
        },
      });
      getData(`/api/team-players/${team_name_or_id}`, receivePlayerData);
      fetchedData.current = true;
    }
  });

  // Info Popover control
  const [openPopover, setOpenPopover] = React.useState(0)
  const open = (user) => setOpenPopover(user);
  const close = () => setOpenPopover(0);

  return (
    <ChakraProvider theme={theme}>
      <Header react_navigate={navigate} signed_in={user != {}}></Header>
      <Box textAlign="center" fontSize="xl" mt="50px">
          <Center minH="500px">
            { isUserMembershipPending && responseReceived.current &&
              <Box mt={20} mb={40}>
                <Text fontSize="lg">Your request to join <b>{teamName}</b> has not been accepted yet.</Text>
                <Button my={4} size='sm' onClick={ () => removePlayer(user['user_id']) }>Cancel Request</Button>
              </Box>
            }
            { !userIsOnTeam && responseReceived.current &&
              <Box mt={20} mb={40}>
                <Text fontSize="lg">You are not on <b>{teamName}</b>. Would you like to request to join?</Text>
                <Button my={4} size='sm' onClick={ () => joinTeam() }>Join</Button>
              </Box>
            }
            { userIsOnTeam && !isUserMembershipPending &&
              <Table size="sml" maxWidth="600px" my="50px" mx="20px">
                <Thead fontSize="0.6em">
                  <Tr>
                    <Th w="33%">Player</Th>
                    <Th w="33%">Role</Th>
                  </Tr>
                </Thead>
                <Tbody fontSize="0.8em">
                  {
                    players && players.map((player) => (

                      <Tr key={player.user_id}>
                        <Td py="10px">
                            <Popover isOpen={player.user_id == openPopover}>
                              <PopoverTrigger>
                                <div onClick={() => open(player.user_id)} style={{cursor: 'pointer'}}>
                                  <span>
                                    {player.user_id == user['user_id'] ? <b>{player.name} (You)</b> : player.name}
                                  </span>
                                  <Icon as={ChevronDownIcon} w={4} h={4} />
                                </div>
                              </PopoverTrigger>
                              <PopoverContent p={5} color='white' bg='blue.800' >
                                <PopoverArrow />
                                <PopoverCloseButton onClick={close} />
                                <Stack>
                                  <a href={`mailto:${player.email}`}>
                                    <Box color="#ffffffbb" _hover={{color: "#ffffffff"}}>
                                      <IconButton size='xs' icon={<EmailIcon />} bg='#ffffff33' color="#ffffff99" mr="10px" _hover={{bg: "#ffffff55"}}/>
                                      {player.email}
                                    </Box>
                                  </a>
                                  <a href={`sms:408-219-7030`}>
                                    <Box color="#ffffffbb" _hover={{color: "#ffffffff"}}>
                                      <IconButton size='xs' icon={<ChatIcon />} bg='#ffffff33' color="#ffffff99" mr="10px" _hover={{bg: "#ffffff55"}}/>
                                      408-219-7030
                                    </Box>
                                  </a>
                                </Stack>

                              </PopoverContent>
                            </Popover>
                        </Td>
                        {
                          isUserCaptain &&
                          <Td>
                            <Select size='xs' value={player.role} onChange={e => roleSelectionChange(player, e.target.value)}>
                              <option value='full'>Full Time</option>
                              <option value='half'>Half Time</option>
                              <option value='sub'>Sub</option>
                              <option value='captain'>Captain</option>
                              <option disabled />
                              <option value='remove'>Remove Player</option>
                            </Select>
                          </Td>
                        }
                        {
                          !isUserCaptain &&
                          <Td>{player.role}</Td>
                        }

                      </Tr>
                   ))
                  }
                </Tbody>
              </Table>
            }
          </Center>
      </Box>

      <AlertDialog
        isOpen={isOpen}
        leastDestructiveRef={cancelRef}
        onClose={onClose}>
        <AlertDialogOverlay>
          <AlertDialogContent>
            <AlertDialogHeader fontSize='lg' fontWeight='bold'>
              Remove {`${playerPendingRemoval.name} (${playerPendingRemoval.email})`} from the team?
            </AlertDialogHeader>

            <AlertDialogBody>
              You cannot undo this action. {playerPendingRemoval.name} will need to re-request team access to return.
            </AlertDialogBody>

            <AlertDialogFooter>
              <Button ref={cancelRef} onClick={cancelRemovePlayer}>
                Cancel
              </Button>
              <Button colorScheme='red' onClick={confirmRemovePlayer} ml={3}>
                Remove
              </Button>
            </AlertDialogFooter>
          </AlertDialogContent>
        </AlertDialogOverlay>
      </AlertDialog>

      <Footer/>
    </ChakraProvider>
  );
}

export default Team;
