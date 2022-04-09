import {
  Box,
  useColorModeValue,
} from '@chakra-ui/react';
import React, { useEffect } from 'react';
import { useNavigate, useParams } from "react-router-dom";
import { checkLogin, getAuthHeader, getData } from '../utils';

export default function Reply() {

  let { game_id, team_id, user_id, response } = useParams();
  let navigate = useNavigate();

  function submitReply() {

    let data = {
      game_id: game_id,
      team_id: team_id,
      user_id: user_id,
      response: response,
    };

    fetch(`/api/game/reply/${game_id}/for-team/${team_id}`, {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json', 'Authorization': getAuthHeader()},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status == 200) {
      }
      navigate(`/game/${game_id}/for-team/${team_id}`);
    });
  };

  useEffect(() => {
    checkLogin(navigate).then( data => {
        if (data.user_id) {
          submitReply();
        }
    });
  });

  return (
    <Box bg={useColorModeValue('gray.50', 'gray.800')}>
    </Box>
  );
  }