import dayjs from 'dayjs';
import { CalendarIcon, ExternalLinkIcon } from '@chakra-ui/icons';
import {
  Badge,
  Box,
  Button,
  Center,
  ChakraProvider,
  FormControl,
  Grid,
  HStack,
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
  Th,
  Tr,
  theme,
  useColorModeValue,
  useDisclosure,
} from '@chakra-ui/react';
import React, {useEffect, useRef, useState} from 'react';
import TagManager from 'react-gtm-module'
import { useNavigate, useParams } from "react-router-dom";

import { ButtonWithTip } from '../components/ButtonWithTip';
import { ColorModeSwitcher } from '../components/ColorModeSwitcher';
import { Header } from '../components/Header';
import { ReplyBox } from '../components/ReplyBox';
import { Footer } from '../components/Footer';
import { checkLogin, getAuthHeader, getData, getPageData } from '../utils';

function Home() {

  let navigate = useNavigate();

  // Popover control
  const [openPopover, setOpenPopover] = React.useState(0)
  const open = (user) => setOpenPopover(user);
  const close = () => setOpenPopover(0);

  // Modal dialog control (join team)
  const { isOpen, onOpen, onClose } = useDisclosure()
  const joinTeamRef = React.useRef();

  // Fetch data
  const fetchedData = useRef(false);
  const [lastRefresh, setLastRefresh] = React.useState(null)
  const [pageError, setPageError] = React.useState(null)
  const [myTeams, setMyTeams] = useState(null);
  const [myGames, setMyGames] = useState(null);
  const [user, setUser] = useState({});

  const loadPageData = async () => {
      const loadDataResult = await getPageData([{url: '/api/team/', handler: setMyTeams},
                                                {url: '/api/games/?upcomingOnly', handler: setMyGames}],
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
          pageTitle: 'Home',
        },
      });

      checkLogin(navigate).then(result => { setUser(result) });

      loadPageData();
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

  function submitReply(event, user_id, team_id, game_id, response, new_msg, is_goalie) {

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

        getData('/api/games/?upcomingOnly', setMyGames)
        return;
      }
    });
  };

  return (
    <ChakraProvider theme={theme}>

      <Header
        react_navigate={navigate}
        signed_in={user != {}}
        lastRefresh={lastRefresh}
        pageError={pageError}
        />

      <Box fontSize="xl">
          <Center>
            <Table size="sml" maxWidth="800px" my="50px" mx="20px">
              <Thead fontSize="0.6em">
                <Tr>
                  <Th>My Games</Th>
                  <Th w="115px"/>
                </Tr>
              </Thead>
              <Tbody fontSize="0.8em">
                { myGames &&
                  myGames['games'] && myGames['games'].map((game) => (

                    <Tr key={game.game_id}>
                      <Td py="6px">
                         <Text fontWeight={500}>{game['scheduled_at']} ({game['scheduled_how_soon']})</Text>
                         <Text color="gray.500"
                               _hover={{
                                  textDecoration: 'none',
                                  color: "gray.800",
                                }}>
                          <a href={`/game/${game.game_id}/for-team/${game.user_team_id}`}>
                           {myTeams['teams'] && myTeams['teams'].length > 1 ? game.user_team.replaceAll(' ', ' ') : ''} vs {game.vs.replaceAll(' ', ' ')}&nbsp;>
                          </a>
                        </Text>
                      </Td>
                      <Td>
                      <Grid container justifyContent="flex-end">
                          { game.user_role != '' &&
                          <ReplyBox
                            isOpen={game.game_id == openPopover}
                            openHandler={() => open(game.game_id)}
                            closeHandler={close}
                            user_id={user.user_id}
                            team_id={game.user_team_id}
                            game_id={game.game_id}
                            submitHandler={submitReply}
                            user_reply={game.user_reply}
                            editable
                          />
                          }
                      </Grid>
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
                  <Th>My Teams</Th>
                  <Th w='115px'/>
                </Tr>
              </Thead>
              <Tbody fontSize="0.8em">
                { myTeams &&
                  myTeams['teams'] && myTeams['teams'].map((team) => (

                    <Tr key={team.team_id}>
                      <Td py="6px">
                        <a href={`/team/${team.name.replaceAll(' ', '-').toLowerCase()}`}>{team.name} ></a>
                      </Td>
                      <Td py="6px">
                        <HStack>
                          <ButtonWithTip
                            label='Share link to join'
                            icon={<ExternalLinkIcon/>}
                            href={`mailto:?subject=Join%20my%20team%20on%20Hockey%20Reply!&body=Join%20the%20${team.name}%20on%20Hockey%20Reply%20so%20we%20can%20keep%20track%20of%20who%20is%20playing%20in%20our%20games.%0A%0Ahttps%3A%2F%2Fhockeyreply.com%2Fteam%2F${team.name.replaceAll(' ', '-').toLowerCase()}%0A%0AThanks%21`}
                            placement='top'
                            mr={0}
                            />
                          { team.calendar_url &&
                          <ButtonWithTip
                            label='Subscribe to the calendar'
                            icon={<CalendarIcon/>}
                            href={team.calendar_url}
                            placement='top'
                            mr={0}
                            />
                          }
                        </HStack>
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
