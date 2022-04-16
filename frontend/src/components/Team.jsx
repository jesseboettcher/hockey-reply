import {
  ArrowForwardIcon,
  CalendarIcon,
  ChatIcon,
  ChevronDownIcon,
  DownloadIcon,
  EmailIcon,
  ExternalLinkIcon,
} from '@chakra-ui/icons'
import {
  AlertDialog,
  AlertDialogOverlay,
  AlertDialogContent,
  AlertDialogHeader,
  AlertDialogBody,
  AlertDialogFooter,
  Box,
  Button,
  Center,
  ChakraProvider,
  HStack,
  Icon,
  Input,
  IconButton,
  Link,
  Popover,
  PopoverArrow,
  PopoverCloseButton,
  PopoverContent,
  PopoverTrigger,
  Select,
  Stack,
  Table,
  Tbody,
  Tr,
  Th,
  Td,
  Thead,
  Text,
  theme,
  Tooltip,
  useColorModeValue,
  useDisclosure,
  useToast
} from '@chakra-ui/react';
import _ from "lodash";
import React, {useEffect, useRef, useState} from 'react';
import TagManager from 'react-gtm-module'
import { useNavigate, useParams } from "react-router-dom";

import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { checkLogin, getAuthHeader, getData } from '../utils';

function Team() {

  let { team_name_or_id } = useParams();
  let navigate = useNavigate();
  const toast = useToast();

  // Remove Player alert
  const [playerPendingRemoval, setPlayerPendingRemoval] = React.useState({})
  const { isAlertOpen, onAlertOpen, onAlertClose } = useDisclosure()
  const [openAlert, setOpenAlert] = React.useState(false)
  const cancelAlertRef = React.useRef()

  const tipBackground = useColorModeValue('#EDF2F7', 'whiteAlpha.200');
  const tipTextColor = useColorModeValue('gray.500', 'gray.200');

  // Player number updates
  const submitPlayerChangesTimer = React.useRef();
  const [pendingNumberChanges, setPendingNumberChanges] = React.useState({});

  // Popover control (player contact info)
  const { isOpen, onOpen, onClose } = useDisclosure();
  const cancelRef = React.useRef();
  const [openPopover, setOpenPopover] = React.useState(0)
  const open = (user) => setOpenPopover(user);
  const close = () => setOpenPopover(0);

  // Fetched data
  const [userIsOnTeam, setUserIsOnTeam] = useState(false);
  const [team, setTeam] = useState([]);
  const [teamId, setTeamId] = useState(0);
  const [teamName, setTeamName] = useState(null);
  const [players, setPlayers] = useState([]);
  const [user, setUser] = useState(0);
  const isUserCaptain = user['role'] == 'captain';
  const isUserMembershipPending = user['role'] == '';
  const calendar_url = team.teams ? team.teams[0].calendar_url : null;

  const fetchedData = useRef(false);
  const responseReceived = useRef(false);

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

  function receivePlayerData(body) {

    let serverReplies = body;
    responseReceived.current = true;

    if (serverReplies['result'] && serverReplies['result'] == 'USER_NOT_ON_TEAM') {
      setUserIsOnTeam(false);
      setTeamName(body['team_name']);
      setTeamId(body['team_id']);
      return;
    }

    if (!_.has(body, 'players')) {
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
    getData(`/api/team/${body['team_id']}`, setTeam);
  }

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

      // Save this player while we present a confirmation dialog which will complete (or clear)
      // the operation
      setPlayerPendingRemoval(player);
      onOpen();
      return;
    }

    // Otherwise, apply the player role change
    let data = {
      team_id: teamId,
      user_id: player['user_id'],
      role: role
    };

    fetch(`/api/player-role`, {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json', 'Authorization': getAuthHeader()},
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

    // Called by the confirm action in the confirmation dialog, perform the actual removal
    let data = {
      team_id: teamId,
      user_id: user_id
    };

    fetch(`/api/remove-player`, {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json', 'Authorization': getAuthHeader()},
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
      headers: {'Content-Type': 'application/json', 'Authorization': getAuthHeader()},
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

  function submitPendingPlayerNumberChanges() {

    for (const [user_id, number] of Object.entries(pendingNumberChanges)) {

      let data = {
        team_name: teamName,
        user_id: user_id,
        team_id: teamId,
        number: number
      };

      fetch(`/api/player-number`, {
        method: "POST",
        credentials: 'include',
        headers: {'Content-Type': 'application/json', 'Authorization': getAuthHeader()},
        body: JSON.stringify(data)
      })
      .then(response => {
        if (response.status == 200) {
          return;
        }
      });
    }
    setPendingNumberChanges({});
  }

  function playerNumberChange(user_id, number) {
    clearTimeout(submitPlayerChangesTimer.current);

    let pending = pendingNumberChanges;
    pending[user_id] = number;
    setPendingNumberChanges(pending);

    submitPlayerChangesTimer.current = setTimeout(submitPendingPlayerNumberChanges, 1000); // 1s
  };

  function isPlayerNumberEditingAllowed(user_id) {

    if (user.user_id == user_id) {
      return true;
    }
    return isUserCaptain;
  };

  function downloadSigninSheet() {

    fetch(`/api/signin-sheet/${teamId}`, {
      method: "GET",
      credentials: 'include',
      headers: {'Content-Type': 'application/json', 'Authorization': getAuthHeader()},
    })
    .then(result => result.blob())
    .then(data => {
      let file = window.URL.createObjectURL(data);
      window.location.assign(file);
    });
    onClose();
  };

  return (
    <ChakraProvider theme={theme}>
      <Header react_navigate={navigate}/>
      <Box minH="500px" textAlign="center" fontSize="xl" mt="50px">
          { teamName &&
          <Center>
            <HStack>
              <Text fontSize='xl' fontWeight='medium'>{teamName}</Text>
              <Tooltip label='Share link to join' placement='top' bg={tipBackground} color={tipTextColor} openDelay={500}>
                <Link href={`mailto:?subject=Join%20my%20team%20on%20Hockey%20Reply!&body=Join%20the%20${teamName}%20on%20Hockey%20Reply%20so%20we%20can%20keep%20track%20of%20who%20is%20playing%20in%20our%20games.%0A%0Ahttps%3A%2F%2Fhockeyreply.com%2Fteam%2F${teamName.replaceAll(' ', '-').toLowerCase()}%0A%0AThanks%21`}>
                  <IconButton ml={3} mr={3} mb='3px' size='xs' icon={<ExternalLinkIcon/>}/>
                </Link>
              </Tooltip>
              { calendar_url &&
              <Tooltip label='Subscribe to the calendar' placement='top' bg={tipBackground} color={tipTextColor} openDelay={500}>
                <Link href={calendar_url}>
                  <IconButton size='xs' icon={<CalendarIcon/>} />
                </Link>
              </Tooltip>
              }
              <Tooltip label='Download sign-in sheet' placement='top' bg={tipBackground} color={tipTextColor} openDelay={500}>
                <Link onClick={() => downloadSigninSheet()} target='_blank' download>
                  <IconButton ml={3} mr={3} mb='3px' size='xs' icon={<DownloadIcon/>}/>
                </Link>
              </Tooltip>
            </HStack>
            </Center>
          }
          <Center>

            { isUserMembershipPending && responseReceived.current &&
              <Box mx={10} mt={20} mb={40}>
                <Text fontSize="lg">Your request to join <b>{teamName}</b> has not been accepted yet.</Text>
                <Button my={4} size='sm' onClick={ () => removePlayer(user['user_id']) }>Cancel Request</Button>
              </Box>
            }
            { !userIsOnTeam && responseReceived.current &&
              <Box mx={10} mt={20} mb={40}>
                <Text fontSize="lg">You are not on <b>{teamName}</b>. Would you like to request to join?</Text>
                <Button my={4} size='sm' onClick={ () => joinTeam() }>Join</Button>
              </Box>
            }
            { userIsOnTeam && !isUserMembershipPending &&
              <Table size="sml" maxWidth="600px" my="50px" mx="20px">
                <Thead fontSize="0.6em">
                  <Tr>
                    <Th w="50%">Player</Th>
                    <Th w="30%">Role</Th>
                    <Th w="20%">Number</Th>
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
                        <Td>
                          <Input
                            placeholder={player.number}
                            size='xs'
                            mt={1}
                            ml={4}
                            width='50px'
                            isDisabled={!isPlayerNumberEditingAllowed(player.user_id)}
                            onChange={e => playerNumberChange(player.user_id, e.target.value)}/>
                        </Td>
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

// TODO add profile page, field for phone numbers, this panel
// <a href={`sms:408-867-5309`}>
//   <Box color="#ffffffbb" _hover={{color: "#ffffffff"}}>
//     <IconButton size='xs' icon={<ChatIcon />} bg='#ffffff33' color="#ffffff99" mr="10px" _hover={{bg: "#ffffff55"}}/>
//     408-867-5309
//   </Box>
// </a>

export default Team;
