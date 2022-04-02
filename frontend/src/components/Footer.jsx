import {
  Box,
  Center,
  Divider,
} from '@chakra-ui/react';
import { ColorModeSwitcher } from '../components/ColorModeSwitcher';

export const Footer = props => {
  return (
    <Box>
      <Divider mt={10}></Divider>
      <Center mt={2}><ColorModeSwitcher justifySelf="flex-middle" /></Center>
    </Box>
  );
};
