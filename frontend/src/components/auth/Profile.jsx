import { ViewIcon, ViewOffIcon } from '@chakra-ui/icons';
import {
  Box,
  Button,
  Flex,
  FormControl,
  FormLabel,
  HStack,
  Input,
  InputGroup,
  InputRightElement,
  Link,
  Stack,
  Text,
  useColorModeValue,
  useToast,
} from '@chakra-ui/react';
import React, { useEffect, useState, useRef } from 'react';
import TagManager from 'react-gtm-module'
import { useNavigate } from "react-router-dom";

import { Header } from '../Header';
import { Footer } from '../Footer';
import { checkLogin, getAuthHeader, getData } from '../../utils';

function checkEmail (email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

export default function Profile() {

  // Fetch data
  const fetchedData = useRef(false);
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

      getData(`/api/profile`, receiveProfileData);
      fetchedData.current = true;
    }
  });

  function receiveProfileData(profileData) {
    setUserId(profileData.user_id);
    setFirstName(profileData.first_name);
    setLastName(profileData.last_name);
    setEmail(profileData.email);
    setPhoneNumber(profileData.phone_number);
    setUsaHockeyNumber(profileData.usa_hockey_number);
  }

  const [userId, setUserId] = React.useState(false);
  const [anyChanges, setAnyChanges] = React.useState(false);
  const [firstName, setFirstName] = React.useState('');
  const [lastName, setLastName] = React.useState('');
  const [email, setEmail] = React.useState('');
  const [phoneNumber, setPhoneNumber] = React.useState('');
  const [usaHockeyNumber, setUsaHockeyNumber] = React.useState('');

  let navigate = useNavigate();
  const toast = useToast();

  const handleChange = (event) => setAnyChanges(true);

  const saveProfileChanges = async event => {

    if (firstName.length == 0) {
      toast({
                title: `Required field, first name`,
                status: 'error', isClosable: true,
            })
      return;
    }
    if (lastName.length == 0) {
      toast({
                title: `Required field, last name`,
                status: 'error', isClosable: true,
            })
      return;
    }

    let data = {
      user_id: userId,
      first_name: firstName,
      last_name: lastName,
      phone_number: phoneNumber,
      usa_hockey_number: usaHockeyNumber
    };

    fetch("/api/profile", {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json', 'Authorization': getAuthHeader()},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status == 200) {
        setAnyChanges(false);
      }
    });
  };

  return (
    <Box>
    <Header />
    <Flex
      minH={'10vh'}
      align={'center'}
      justify={'center'}>
      <Stack spacing={8} mx={'auto'} maxW={'lg'} minW={'md'} py={12} px={6}>
        <Box
          rounded={'lg'}
          bg={useColorModeValue('white', 'gray.700')}
          boxShadow={'lg'}
          p={8}>
            <Stack spacing={5}>
                <FormControl id="email">
                  <FormLabel>Email address:</FormLabel>
                  <Text>
                    {email}
                  </Text>
                </FormControl>

                <HStack>
                  <Box>
                    <FormControl id="firstName">
                      <FormLabel>First Name</FormLabel>
                      <Input type="text" value={firstName} onChange={(e) => {setFirstName(e.target.value); handleChange();}}/>
                    </FormControl>
                  </Box>

                  <Box>
                    <FormControl id="lastName">
                      <FormLabel>Last Name</FormLabel>
                      <Input type="text" value={lastName} onChange={(e) => {setLastName(e.target.value); handleChange();}}/>
                    </FormControl>
                  </Box>
                </HStack>

                <FormControl id="usaHockeyNumber">
                  <FormLabel>USA Hockey Number:</FormLabel>
                  <Input type="text" value={usaHockeyNumber} onChange={(e) => {setUsaHockeyNumber(e.target.value); handleChange();}}/>
                </FormControl>

                <FormControl id="phoneNumber">
                  <FormLabel>Phone:</FormLabel>
                  <Input type="text" value={phoneNumber} onChange={(e) => {setPhoneNumber(e.target.value); handleChange();}}/>
                </FormControl>

                <Stack spacing={10} pt={2}>
                  <Button
                    isDisabled={!anyChanges}
                    loadingText="Submitting"
                    size="sm"
                    bg={'gray.400'}
                    color={'white'}
                    onClick={saveProfileChanges}
                    _hover={{
                      bg: 'gray.500',
                    }}>
                    Save Changes
                  </Button>
                </Stack>

                <Stack>
                    <p><Link color={'blue.400'} href='/sign-out'>Sign out ></Link></p>
                </Stack>
            </Stack>
        </Box>
      </Stack>
    </Flex>
    <Footer/>
    </Box>
  );
}
