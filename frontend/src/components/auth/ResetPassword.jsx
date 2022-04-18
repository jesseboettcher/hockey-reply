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
import { useNavigate, useSearchParams } from "react-router-dom";

import { Header } from '../Header';
import { Footer } from '../Footer';

export default function ResetPassword() {

  const [showPassword, setShowPassword] = useState(false);
  const [password, setPassword] = useState('');
  const [searchParams, setSearchParams] = useSearchParams();
  let navigate = useNavigate();
  const toast = useToast();

  const submitPassword = async event => {

    if (password.length < 8) {
      toast({
                title: `Password must be at least 8 characters`,
                status: 'error', isClosable: true,
            })
      return;
    }

    const token = searchParams.get("token")
    if (token == undefined) {
      toast({
                title: `Missing authentication. Retry Forgot Password`,
                status: 'error', isClosable: true,
            })
      return;
    }

    // TODO hash password before sending (HR-7)
    let data = {
      token: token,
      password: password,
    };

    fetch("/api/reset-password", {
      method: "POST",
      credentials: 'include',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify(data)
    })
    .then(response => {
      if (response.status == 200) {
        navigate('/sign-in?event=password_updated', {replace: true});
      }
    });
  };

 useEffect(() => {
    const listener = event => {
      if (event.code === "Enter" || event.code === "NumpadEnter") {
        submitPassword();
      }
    };
    document.addEventListener("keyup", listener);
    return () => {
      document.removeEventListener("keyup", listener);
    };
  }, []);

  return (
    <Box>
    <Header hide_sign_in={true} />
    <Flex
      minH={'50vh'}
      align={'center'}
      justify={'center'}>
      <Stack spacing={8} mx={'auto'} maxW={'lg'} py={12} px={6}>
        <Box
          rounded={'lg'}
          bg={useColorModeValue('white', 'gray.700')}
          boxShadow={'lg'}
          p={8}>
          <Stack spacing={4}>
          <Heading fontSize={'2xl'} textAlign={'center'}>
            Reset Password
          </Heading>

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
                bg={'blue.400'}
                color={'white'}
                _hover={{
                  bg: 'blue.500',
                }}
                onClick={submitPassword}>
                Update Password
              </Button>
            </Stack>


          </Stack>
        </Box>
      </Stack>
    </Flex>
    <Footer/>
    </Box>
  );
}
