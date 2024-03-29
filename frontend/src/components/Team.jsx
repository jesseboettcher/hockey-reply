import {
  ArrowUpIcon,
  ArrowDownIcon,
  CalendarIcon,
  ChatIcon,
  ChevronDownIcon,
  CopyIcon,
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
  FormControl,
  FormLabel,
  HStack,
  Icon,
  Input,
  IconButton,
  Modal,
  ModalBody,
  ModalContent,
  ModalCloseButton,
  ModalFooter,
  ModalHeader,
  ModalOverlay,
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
  useColorModeValue,
  useDisclosure,
  useToast,
  VStack
} from '@chakra-ui/react';
import _ from "lodash";
import React, {useEffect, useRef, useState} from 'react';
import TagManager from 'react-gtm-module'
import { useNavigate, useParams } from "react-router-dom";

import { ButtonWithTip } from '../components/ButtonWithTip';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { checkLogin, getAuthHeader, getData } from '../utils';

export function PlayerInfo(props: React.PropsWithChildren<MyProps>) {

  const hoverColor = useColorModeValue('gray.500', 'gray.400');

  function usaHockeyAction() {

    navigator.clipboard.writeText(props.usaHockeyNumber)
    props.toast({
          title: `Copied to clipboard`,
          status: 'info', isClosable: true,
      })
  }

  return (
    <Popover isOpen={props.isOpen}>
      <PopoverTrigger>
        <div onClick={props.clickHandler} style={{cursor: 'pointer'}}>
          <span>
            {props.label}
          </span>
          <Icon as={ChevronDownIcon} w={4} h={4} />
        </div>
      </PopoverTrigger>
      <PopoverContent p={5}>
        <PopoverArrow />
        <PopoverCloseButton onClick={props.closeHandler} />
        <Stack>
          <a href={`mailto:${props.email}`}>
            <Box _hover={{color: hoverColor}}>
              <IconButton size='xs' icon={<EmailIcon />} mr="10px"/>
              {props.email}
            </Box>
          </a>
          { props.phoneNumber &&
          <a href={`sms:${props.phoneNumber}`}>
            <Box _hover={{color: hoverColor}}>
              <IconButton size='xs' icon={<ChatIcon />} mr="10px"/>
              {props.phoneNumber}
            </Box>
          </a>
          }
          { props.usaHockeyNumber &&
          <a onClick={usaHockeyAction} style={{cursor: 'pointer'}}>
            <Box _hover={{color: hoverColor}}>
              <IconButton size='xs' icon={<CopyIcon />} mr="10px"/>
              {props.usaHockeyNumber}
            </Box>
          </a>
          }
        </Stack>

      </PopoverContent>
    </Popover>
  );
}


export function Team() {

  let { team_name_or_id } = useParams();
  let navigate = useNavigate();
  const toast = useToast();

  // Remove Player alert
  const [playerPendingRemoval, setPlayerPendingRemoval] = React.useState({})

  // Player number updates
  const submitPlayerChangesTimer = React.useRef();
  const [pendingNumberChanges, setPendingNumberChanges] = React.useState({});

  // Popover control (player contact info)
  const { isOpen, onOpen, onClose } = useDisclosure();
  const cancelRef = React.useRef();
  const [openPopover, setOpenPopover] = React.useState(0)
  const open = (user) => setOpenPopover(user);
  const close = () => setOpenPopover(0);

  // Add Goalie Modal
  const pendingNewGoalie = React.useRef({});
  const [isAddGoalieModalOpen, setIsAddGoalieModalOpen] = React.useState(false)
  const OpenAddGoalieModal = (user) => { pendingNewGoalie.current = {}; setIsAddGoalieModalOpen(true); }
  const CloseAddGoalieModal = () => setIsAddGoalieModalOpen(false);

  // Fetched data
  const [userIsOnTeam, setUserIsOnTeam] = useState(false);
  const [team, setTeam] = useState([]);
  const [teamId, setTeamId] = useState(0);
  const [teamName, setTeamName] = useState(null);
  const [players, setPlayers] = useState([]);
  const [goalieList, setGoalieList] = useState({});
  const [user, setUser] = useState(0);
  const [isUserCaptain, setIsUserCaptain] = useState(null);
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

    let sorted = serverReplies['players'].sort(function(a, b) {
      let a_split = a.name.split(' ');
      let a_last = a_split[a_split.length - 1];

      let b_split = b.name.split(' ');
      let b_last = b_split[b_split.length - 1];

      return a_last.localeCompare(b_last, undefined, { sensitivity: 'base' });
    });

    setUserIsOnTeam(true);
    setPlayers(serverReplies['players']);//body['players'])
    setUser(body['user'])
    setIsUserCaptain(body['user']['role'] == 'captain')
    setTeamId(body['team_id']);
    setTeamName(body['team_name'])
    getData(`/api/team/${body['team_id']}`, setTeam);
    getData(`/api/goalies/${body['team_id']}`, setGoalieList);
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

  function submitAddGoalie() {

    CloseAddGoalieModal();

    if (!pendingNewGoalie.current.hasOwnProperty('user_id')) {
      pendingNewGoalie.current['user_id'] = 0; // Unrostered
    }

    let data = {
      team_id: teamId,
      user_id: pendingNewGoalie.current['user_id'],
      nickname: pendingNewGoalie.current['nickname'],
      phone_number: pendingNewGoalie.current['phone_number'],
    };

    fetch(`/api/add-goalie`, {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json', 'Authorization': getAuthHeader()},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status === 200) {
        window.location.reload();
      }
    });
  };

  function updateGoalieOrder(goalie_id, direction) {
    let data = {
      team_id: teamId,
      goalie_id: goalie_id,
      direction: direction
    };

    fetch(`/api/update-goalie-order`, {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json', 'Authorization': getAuthHeader()},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status === 200) {
        window.location.reload();
      }
    });
  }

  function removeGoalie(goalie_id) {
    let data = {
      team_id: teamId,
      goalie_id: goalie_id,
    };

    fetch(`/api/remove-goalie`, {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json', 'Authorization': getAuthHeader()},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status === 200) {
        window.location.reload();
      }
    });
  }

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

  function dbRoleToDisplayRole(dbRole) {
    if (dbRole == 'captain') {
      return 'Captain';
    }
    if (dbRole == 'full') {
      return 'Full Time';
    }
    if (dbRole == 'half') {
      return 'Half Time';
    }
    if (dbRole == 'sub') {
      return 'Sub';
    }
    return '';
  }

  const allEmails = players.map(player => player.email);

  return (
    <ChakraProvider theme={theme}>
      <Header react_navigate={navigate}/>
      <Box minH="500px" textAlign="center" fontSize="xl" mt="50px">
          { teamName &&
          <Center>
            <VStack>
              <Text fontSize='xl' fontWeight='medium'>{teamName}</Text>
              <HStack>
                <ButtonWithTip
                  label='Share link to join'
                  icon={<ExternalLinkIcon/>}
                  href={`mailto:?subject=Join%20my%20team%20on%20Hockey%20Reply!&body=Join%20the%20${teamName}%20on%20Hockey%20Reply%20so%20we%20can%20keep%20track%20of%20who%20is%20playing%20in%20our%20games.%0A%0Ahttps%3A%2F%2Fhockeyreply.com%2Fteam%2F${teamName.replaceAll(' ', '-').toLowerCase()}%0A%0AThanks%21`}
                  placement='bottom'
                  mr={3}
                  />
                { calendar_url &&
                <ButtonWithTip
                  label='Subscribe to the calendar'
                  icon={<CalendarIcon/>}
                  href={calendar_url}
                  placement='bottom'
                  mr={3}
                  />
                }
                <ButtonWithTip
                  label='Download sign-in sheet'
                  icon={<DownloadIcon/>}
                  linkDownloadAction={() => downloadSigninSheet()}
                  placement='bottom'
                  mr={3}
                  />
                <ButtonWithTip
                  label='Email everyone'
                  icon={<EmailIcon/>}
                  href={`mailto:${allEmails.join(',')},?subject=${teamName}:`}
                  placement='bottom'
                  mr={3}
                  />
              </HStack>
            </VStack>
            </Center>
          }
          <Center>

            { isUserMembershipPending && responseReceived.current &&
              <Box mx={10} mt={20} mb={40}>
                <Text fontSize="lg">Your request to join <b>{teamName}</b> has not been accepted yet.</Text>
                <Button my={4} size='sm' onClick={ () => removePlayer(user['user_id']) }>Cancel Request</Button>
              </Box>
            }
            { !userIsOnTeam && isUserCaptain != null && responseReceived.current &&
              <Box mx={10} mt={20} mb={40}>
                <Text fontSize="lg">You are not on <b>{teamName}</b>. Would you like to request to join?</Text>
                <Button my={4} size='sm' onClick={ () => joinTeam() }>Join</Button>
              </Box>
            }
            { userIsOnTeam && isUserCaptain != null && !isUserMembershipPending &&
              <Table size="sml" maxWidth="600px" mt="50px" mx="20px">
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
                          <PlayerInfo
                            isOpen={player.user_id == openPopover}
                            clickHandler={() => open(player.user_id)}
                            label={player.user_id == user['user_id'] ? <b>{player.name} (You)</b> : player.name}
                            closeHandler={() => close()}
                            email={player.email}
                            phoneNumber={player.phone_number}
                            usaHockeyNumber={player.usa_hockey_number}
                            toast={toast}
                          />
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
                          <Td>{dbRoleToDisplayRole(player.role)}</Td>
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

          { isUserCaptain && players /* make sure data has loaded */ &&
          <>
            <Center>
              <Table size="sml" maxWidth="600px" mt="50px" mx="20px">
                <Thead fontSize="0.6em">
                  <Tr>
                    <Th w="5%"></Th>
                    <Th w="35%">Goalie</Th>
                    <Th w="25%">Nickname</Th>
                    <Th w="25%">Phone Number</Th>
                    <Th w="15%"></Th>
                  </Tr>
                </Thead>
                <Tbody fontSize="0.8em">
                  { 'goalies' in goalieList && goalieList['goalies'].map((goalie, index) => (
                  <Tr key={index}>
                    <Td>
                      <IconButton size='xs' icon={<ArrowUpIcon />} onClick={ () => { updateGoalieOrder(goalie.goalie_id, 'up'); } } mr="10px"/>
                      <IconButton size='xs' icon={<ArrowDownIcon />} onClick={ () => { updateGoalieOrder(goalie.goalie_id, 'down'); } } mr="10px"/>
                    </Td>
                    <Td>
                      <Text size='xs'>{goalie.name}</Text>
                    </Td>
                    <Td>
                      <Text size='xs'>{goalie.nickname}</Text>
                    </Td>
                    <Td>
                      <Text size='xs'>{goalie.phone_number}</Text>
                    </Td>
                    <Td>
                      <Button my={2} size='xs' onClick={ () => { removeGoalie(goalie.goalie_id); } }>Remove</Button>
                    </Td>
                  </Tr>
                ))}
                </Tbody>
              </Table>
            </Center>
            <Button my={2} size='xs' onClick={ () => {OpenAddGoalieModal()} }>Add Goalie</Button>
          </>
          }
 
          { userIsOnTeam && isUserCaptain != null && !isUserMembershipPending &&
            <Center mt="40px">
              <Button my={4} size='sm' onClick={ () => {
                  let myself = {};
                  myself.user_id = user.user_id;
                  myself.name = "yourself";
                  myself.email = null;
                  setPlayerPendingRemoval(myself);
                  onOpen();
                } }>Leave Team</Button>
            </Center>
          }
    </Box>

      <AlertDialog
        isOpen={isOpen}
        leastDestructiveRef={cancelRef}
        onClose={onClose}>
        <AlertDialogOverlay>
          <AlertDialogContent>
            { playerPendingRemoval.email &&
              <AlertDialogHeader fontSize='lg' fontWeight='bold'>
                Remove {`${playerPendingRemoval.name} (${playerPendingRemoval.email})`} from the team?
              </AlertDialogHeader>
            }
            { !playerPendingRemoval.email &&
              <AlertDialogHeader fontSize='lg' fontWeight='bold'>
              Remove {`${playerPendingRemoval.name}`} from the team?
              </AlertDialogHeader>
            }

            { playerPendingRemoval.email &&
              <AlertDialogBody>
                You cannot undo this action. {playerPendingRemoval.name} will need to re-request team access to return.
              </AlertDialogBody>
            }
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

      <>
        <Modal
          isOpen={isAddGoalieModalOpen}
          onClose={ () => CloseAddGoalieModal() }
        >
          <ModalOverlay />
          <ModalContent>
            <ModalHeader>Add Goalie</ModalHeader>
            <ModalCloseButton />

            <ModalBody pb={6}>
              <FormControl>
                <FormLabel>User</FormLabel>
                <Select size='xs' mb={4} onChange={e => { pendingNewGoalie.current['user_id']= e.target.value }}>
                <option value='0'>Unrostered</option>
                  <option disabled></option>
                  { players && players.map((player, index) => (
                  <option key={index} value={player.user_id}>{player.name}</option>
                  ))}
                </Select>
              </FormControl>
              <FormControl>
                <FormLabel>Nickname</FormLabel>
                <Input size='xs' placeholder='' onChange={e => { pendingNewGoalie.current['nickname']= e.target.value }}/>
              </FormControl>
              <FormControl mt={4}>
                <FormLabel>Phone Number</FormLabel>
                <Input size='xs' placeholder='' onChange={e => { pendingNewGoalie.current['phone_number']= e.target.value }}/>
              </FormControl>
            </ModalBody>

            <ModalFooter>
              <Button colorScheme='blue' mr={3} onClick={ () => submitAddGoalie() }>Save</Button>
              <Button onClick={ () => { pendingNewGoalie.current = {}; CloseAddGoalieModal() }}>Cancel</Button>
            </ModalFooter>
          </ModalContent>
        </Modal>
      </>

      <Footer/>
    </ChakraProvider>
  );
}

export default Team;
