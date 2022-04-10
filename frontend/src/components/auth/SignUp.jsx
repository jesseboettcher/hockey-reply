import { ViewIcon, ViewOffIcon } from '@chakra-ui/icons';
import {
  Box,
  Button,
  Flex,
  FormControl,
  FormLabel,
  Heading,
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
import { Header } from '../Header';
import { Footer } from '../Footer';
import { useNavigate } from "react-router-dom";
import TagManager from 'react-gtm-module'

function checkEmail (email) {
  return /^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(email)
}

export default function SignupCard() {

  const [showPassword, setShowPassword] = useState(false);
  const [password, setPassword] = useState('');
  const [userEmail, setUserEmail] = useState('');
  const firstNameRef = React.useRef();
  let navigate = useNavigate();
  const toast = useToast();
  const fetchedData = useRef(false);

  const submitSignUp = async event => {

    event.preventDefault();

    if (firstNameRef.current.value.length == 0) {
      toast({
                title: `Required field, first name`,
                status: 'error', isClosable: true,
            })
      return;
    }
    if (password.length < 8) {
      toast({
                title: `Password must be at least 8 characters`,
                status: 'error', isClosable: true,
            })
      return;
    }
    if (!checkEmail(userEmail)) {
      toast({
                title: `Valid email address required`,
                status: 'error', isClosable: true,
            })
      return;
    }

    // TODO hash password before sending (HR-7)
    let data = {
      first_name: firstNameRef.current.value,
      email: userEmail,
      password: password,
    };

    fetch("/api/new-user", {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status == 200) {
        navigate('/games', {replace: true});
      }
    });
  };

  useEffect(() => {
    if (!fetchedData.current) {
      TagManager.dataLayer({
        dataLayer: {
          event: 'pageview',
          pagePath: window.location.pathname,
          pageTitle: 'Sign Up',
        },
      });
      fetchedData.current = true;
    }
  });

  return (
    <Box>
    <Header hide_sign_in={true} />
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
            <Stack spacing={4}>
              <form onSubmit={submitSignUp}>
                <HStack>
                  <Box>
                    <FormControl id="firstName" isRequired>
                      <FormLabel>First Name</FormLabel>
                      <Input type="text" ref={firstNameRef}/>
                    </FormControl>
                  </Box>

                  <Box>
                    <FormControl id="lastName">
                      <FormLabel>Last Name</FormLabel>
                      <Input type="text" />
                    </FormControl>
                  </Box>
                </HStack>

                <FormControl id="email" isRequired>
                  <FormLabel>Email address</FormLabel>
                  <Input type="email" onChange={(e) => setUserEmail(e.target.value) }/>
                </FormControl>

                <FormControl id="password" isRequired>
                  <FormLabel>Password</FormLabel>
                  <InputGroup>
                    <Input type={showPassword ? 'text' : 'password'} onChange={(e) => setPassword(e.target.value) } />
                    <InputRightElement h={'full'}>
                      <Button
                        variant={'ghost'}
                        onClick={() =>
                          setShowPassword((showPassword) => !showPassword)
                        }>
                        {showPassword ? <ViewIcon /> : <ViewOffIcon />}
                      </Button>
                    </InputRightElement>
                  </InputGroup>
                </FormControl>

                <Stack spacing={10} pt={2}>
                  <Button
                    loadingText="Submitting"
                    size="lg"
                    bg={'blue.400'}
                    color={'white'}
                    _hover={{
                      bg: 'blue.500',
                    }}
                    type="submit">
                    Sign up
                  </Button>
                </Stack>

                <Stack pt={6}>
                    <p>Already a user? <Link color={'blue.400'} href='sign-in'>Sign in ></Link></p>
                </Stack>
              </form>
            </Stack>
        </Box>
      </Stack>
    </Flex>
    <Footer/>
    </Box>
  );
}
