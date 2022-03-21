import React, {useEffect, useRef, useState} from 'react';
import {
  ChakraProvider,
  Box,
  Button,
  Text,
  Link,
  List,
  ListIcon,
  ListItem,
  VStack,
  Code,
  Grid,
  theme,
  Select,
  useToast
} from '@chakra-ui/react';
import { ArrowForwardIcon } from '@chakra-ui/icons'
import { useNavigate, useParams } from "react-router-dom";
import { ColorModeSwitcher } from '../components/ColorModeSwitcher';
import { checkLogin } from '../utils';

function getData(url, arrayName, setFn) {
    fetch(url, {credentials: 'include'})
    .then(r =>  r.json().then(data => ({status: r.status, body: data})))
      .then(obj => { return setFn(obj.body[arrayName]) });
}

function respondToJoinRequest(request, requestRoles, toast) {

  if (requestRoles[request.email] == undefined) {
    toast({
        title: `Must select a role before adding player to team`,
        status: 'error', isClosable: true,
    });
    return;
  }

  let data = {
    team_id: request.team_id,
    user_id: request.user_id,
    role: requestRoles[request.email]
  };

  fetch("/api/accept-join", {
    method: "POST",
    credentials: 'include',
    headers: {'Content-Type': 'application/json'},
    body: JSON.stringify(data)
  })
  .then(response => {
    if (response.status == 200) {
      // TODO refresh
      return;
    }
    toast({
        title: `Accept failed`,
        status: 'error', isClosable: true,
    });
  });
}

function Team() {

  let { team_id } = useParams();
  let navigate = useNavigate();
  const [teams, setTeams] = useState([]);
  const [joinRequests, setJoinRequests] = useState([]);
  const [requestRoles, setRequestRoles] = useState({});
  const fetchedData = useRef(false);
  const toast = useToast();

  const acceptRequest = async event => {

  };

  function roleSelectionChange(request, role) {

    requestRoles[request.email] = role;
    console.log(request)
    console.log(role)

  };

  useEffect(() => {
    checkLogin(navigate);

    if (!fetchedData.current) {
      if (team_id === undefined) {
        getData('/api/team/', 'teams', setTeams);
        getData('/api/join-requests/', 'join_requests', setJoinRequests);
      }
      else {
        getData(`/api/team/${team_id}`, 'teams', setTeams);
        getData(`/api/join-requests/${team_id}`, 'join_requests', setJoinRequests);
      }
      fetchedData.current = true;
    }
  });

  return (
    <ChakraProvider theme={theme}>
      <Box textAlign="center" fontSize="xl">
        <Grid minH="100vh" p={3}>
          <ColorModeSwitcher justifySelf="flex-end" />
            
            <List spacing={3}>
              { teams.map((team) => (
                <ListItem key={team.team_id}>
                  <ListIcon  color='green.500' />
                  {team.name} ({team.player_count} players)
                </ListItem>
               ))
              }
            </List>
            <List spacing={3}>
              { joinRequests.map((request) => (
                <ListItem key={request.email}>
                  <ListIcon  color='green.500' />
                  {request.email} ({request.requested_at})
                  <Select placeholder='Role' onChange={e => roleSelectionChange(request, e.target.value)}>
                    <option value='full'>Full Time</option>
                    <option value='half'>Half Time</option>
                    <option value='sub'>Sub</option>
                    <option value='captain'>Captain</option>
                  </Select>
                    <Button rightIcon={<ArrowForwardIcon />}
                            colorScheme='teal'
                            variant='outline'
                            onClick={() => respondToJoinRequest(request, requestRoles, toast)}>
                    Accept
                  </Button>
                </ListItem>
               ))
              }
            </List>


        </Grid>
      </Box>
    </ChakraProvider>
  );
}

export default Team;
