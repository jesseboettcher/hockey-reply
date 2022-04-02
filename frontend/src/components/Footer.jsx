import {
  Box,
  Center,
  Divider,
} from '@chakra-ui/react';
import { ColorModeSwitcher } from '../components/ColorModeSwitcher';

export const Footer = props => {
  return (
    <Box my={10}>
      <Divider></Divider>
      <Center mt={4}><ColorModeSwitcher justifySelf="flex-middle" /></Center>
    </Box>
  );
};
