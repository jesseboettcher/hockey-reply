import {
  Badge,
  Box,
  Center,
  Divider,
  HStack,
  Image,
  Link,
  Stack,
  Text,
  Tooltip,
  useColorModeValue
} from '@chakra-ui/react';
import { ColorModeSwitcher } from '../components/ColorModeSwitcher';

export function IceHockeyGuy() {
  const hoverColor = useColorModeValue('#EDF2F7', 'whiteAlpha.200');
  const tipBackground = useColorModeValue('#EDF2F7', 'whiteAlpha.200');
  const tipTextColor = useColorModeValue('gray.500', 'gray.200');

  return (
    <Tooltip label='Send feedback' placement='top' bg={tipBackground} color={tipTextColor} openDelay={500}>
      <Link href="mailto:jesse@hockeyreply.com?subject=Feedback%20on%20Hockey%20Reply">
        <Image bg='whiteAlpha.50'
               boxSize="40px"
               src='ice_hockey_guy.png'
               borderRadius='6px'
               _hover={{
                  bg: hoverColor,
                }}/>
      </Link>
    </Tooltip>
    )
}

export const Footer = props => {
  return (
    <Box>
      <Divider></Divider>
      <Center py={15}>
        <Stack>
          <Center>
            <HStack>
            <IceHockeyGuy/>
            <ColorModeSwitcher justifySelf="flex-right" />
            </HStack>
          </Center>
          <Box>
            <HStack>
            </HStack>
          </Box>
        </Stack>
      </Center>
    </Box>
  );
};
