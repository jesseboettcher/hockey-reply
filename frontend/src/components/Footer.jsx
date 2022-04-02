import {
  Box,
  Center,
  Divider,
  Stack,
  Text,
} from '@chakra-ui/react';
import { ColorModeSwitcher } from '../components/ColorModeSwitcher';

export const Footer = props => {
  return (
    <Box>
      <Divider></Divider>
      <Center py={15}>
        <Stack>
        <ColorModeSwitcher justifySelf="flex-right" />
        <Box>
        <Text color="red.600" fontWeight="medium">WARNING: Work in progress. Lots of issues.</Text>
        </Box>
        </Stack>
      </Center>
    </Box>
  );
};
