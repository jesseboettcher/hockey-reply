import { CalendarIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import {
  Box,
  Button,
  Center,
  ChakraProvider,
  FormControl,
  IconButton,
  Input,
  Link,
  Modal,
  ModalOverlay,
  ModalContent,
  ModalHeader,
  ModalCloseButton,
  ModalBody,
  ModalFooter,
  Table,
  Tbody,
  Td,
  Text,
  Thead,
  Tooltip,
  Th,
  Tr,
  theme,
  useColorModeValue,
  useDisclosure,
} from '@chakra-ui/react';
import React, {useEffect, useRef, useState} from 'react';
import TagManager from 'react-gtm-module'
import { useNavigate, useParams } from "react-router-dom";

import { ColorModeSwitcher } from '../components/ColorModeSwitcher';
import { Header } from '../components/Header';
import { Footer } from '../components/Footer';
import { checkLogin, getAuthHeader, getData, logout, MyLink } from '../utils';

function Home() {

  let navigate = useNavigate();

  // Modal dialog control (join team)
  const { isOpen, onOpen, onClose } = useDisclosure()
  const joinTeamRef = React.useRef();

  const tipBackground = useColorModeValue('#EDF2F7', 'whiteAlpha.200');
  const tipTextColor = useColorModeValue('gray.500', 'gray.200');

  // Fetch data
  const fetchedData = useRef(false);
  const [myTeams, setMyTeams] = useState([]);
  const [myGames, setMyGames] = useState([]);
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

      checkLogin(navigate).then(result => { setUser(result) });

      getData('/api/team/', setMyTeams)
      getData('/api/games/?upcomingOnly', setMyGames)

      fetchedData.current = true;
    }
  });

  function joinTeam() {
    let data = {
      team_name: joinTeamRef.current.value,
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

  return (
    <ChakraProvider theme={theme}>

      <Header react_navigate={navigate} signed_in={user != {}}></Header>

      <Box fontSize="xl">
          <Center>
            <Table size="sml" maxWidth="800px" my="50px" mx="20px">
              <Thead fontSize="0.6em">
                <Tr>
                  <Th w="100%">My Games</Th>
                  <Th/>
                </Tr>
              </Thead>
              <Tbody fontSize="0.8em">
                {
                  myGames['games'] && myGames['games'].map((game) => (

                    <Tr key={game.game_id}>
                      <Td py="6px">
                         <Text fontWeight={500}>{game['scheduled_at']} (in&nbsp;{game['scheduled_how_soon']})</Text>
                         <Text color="gray.500"
                               _hover={{
                                  textDecoration: 'none',
                                  color: "gray.800",
                                }}>
                          <a href={`/game/${game.game_id}/for-team/${game.user_team_id}`}>
                           {myTeams['teams'] && myTeams['teams'].length > 1 ? game.user_team : ''} vs {game.vs} >
                          </a>
                        </Text>
                      </Td>
                    </Tr>
                 ))
                }
              </Tbody>
            </Table>
          </Center>
          <Center>
            <Table size="sml" maxWidth="800px" my="50px" mx="20px">
              <Thead fontSize="0.6em">
                <Tr>
                  <Th w="70%">My Teams</Th>
                  <Th w="30%"/>
                </Tr>
              </Thead>
              <Tbody fontSize="0.8em">
                {
                  myTeams['teams'] && myTeams['teams'].map((team) => (

                    <Tr key={team.team_id}>
                      <Td py="6px">
                        <a href={`/team/${team.name.replaceAll(' ', '-').toLowerCase()}`}>{team.name} ></a>
                      </Td>
                      <Td py="6px">
                        <Tooltip label='Share link to join' placement='top' bg={tipBackground} color={tipTextColor} openDelay={500}>
                          <Link href={`mailto:?subject=Join%20my%20team%20on%20Hockey%20Reply!&body=Join%20the%20${team.name}%20on%20Hockey%20Reply%20so%20we%20can%20keep%20track%20of%20who%20is%20playing%20in%20our%20games.%0A%0Ahttps%3A%2F%2Fhockeyreply.com%2Fteam%2F${team.name.replaceAll(' ', '-').toLowerCase()}%0A%0AThanks%21`}>
                            <IconButton size='xs' icon={<ExternalLinkIcon/>} mx={3} />
                          </Link>
                        </Tooltip>
                        { team.calendar_url &&
                        <Tooltip label='Subscribe to the calendar' placement='top' bg={tipBackground} color={tipTextColor} openDelay={500}>
                          <Link href={team.calendar_url}>
                            <IconButton size='xs' icon={<CalendarIcon/>} mx={3}/>
                          </Link>
                        </Tooltip>
                        }
                      </Td>
                    </Tr>
                 ))
                }
                <Tr>
                 &nbsp;
                </Tr>
                <Tr>
                  <Button size='sm' onClick={onOpen}>Join a Team</Button>
                </Tr>
              </Tbody>
            </Table>
          </Center>
      </Box>

      <Modal
              isOpen={isOpen}
              onClose={onClose}
            >
        <ModalOverlay />
        <ModalContent>
          <ModalHeader>Join a team</ModalHeader>
          <ModalCloseButton />
          <ModalBody pb={6}>
            <FormControl>
              <Input ref={joinTeamRef} placeholder='Team name' />
            </FormControl>
          </ModalBody>

          <ModalFooter>
            <Button onClick={e => joinTeam()} colorScheme='blue' mr={3}>
              Join
            </Button>
            <Button onClick={onClose}>Cancel</Button>
          </ModalFooter>
        </ModalContent>
      </Modal>

      <Footer></Footer>
    </ChakraProvider>
  );
}

export default Home;
