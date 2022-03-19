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
import React, { useEffect, useState } from 'react';
import { useNavigate } from "react-router-dom";

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

  const submitSignUp = async event => {

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
    const listener = event => {
      if (event.code === "Enter" || event.code === "NumpadEnter") {
        submitSignUp();
      }
    };
    document.addEventListener("keyup", listener);
    return () => {
      document.removeEventListener("keyup", listener);
    };
  }, []);

  return (
    <Flex
      minH={'100vh'}
      align={'center'}
      justify={'center'}
      bg={useColorModeValue('gray.50', 'gray.800')}>
      <Stack spacing={8} mx={'auto'} maxW={'lg'} py={12} px={6}>
        <Stack align={'center'}>
          <Heading fontSize={'4xl'} textAlign={'center'}>
            Sign up
          </Heading>
        </Stack>
        <Box
          rounded={'lg'}
          bg={useColorModeValue('white', 'gray.700')}
          boxShadow={'lg'}
          p={8}>
          <Stack spacing={4}>

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
                onClick={submitSignUp}>
                Sign up
              </Button>
            </Stack>

            <Stack pt={6}>
                <p>Already a user? <Link color={'blue.400'} href='sign-in'>Sign in ></Link></p>
            </Stack>

          </Stack>
        </Box>
      </Stack>
    </Flex>
  );
}
