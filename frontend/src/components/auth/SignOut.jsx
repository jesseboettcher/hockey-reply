// SignOut
//
// Clears the current login token and redirects to the sign-in page

import {
  Box,
  useColorModeValue,
} from '@chakra-ui/react';
import React, { useEffect } from 'react';
import { useNavigate } from "react-router-dom";
import { logout } from '../../utils';

export default function SignOut() {

  let navigate = useNavigate();

  useEffect(() => {
    logout(navigate);
  });

  return (
    <Box bg={useColorModeValue('gray.50', 'gray.800')}>
    </Box>
  );
}
