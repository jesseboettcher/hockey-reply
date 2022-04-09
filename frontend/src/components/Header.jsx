import React from 'react';
import {
  Badge,
  Center,
  ChakraProvider,
  Box,
  Divider,
  Flex,
  Text,
  Link,
  HStack,
  VStack,
  Code,
  Grid,
  Spacer,
  Square,
  Table,
  Tbody,
  Td,
  Thead,
  Th,
  Tr,
  theme,
  useColorModeValue,
} from '@chakra-ui/react';
import { FaMoon, FaSun } from 'react-icons/fa';
import { logout } from '../utils';

import {
  IconButton,
  Button,
  Stack,
  Collapse,
  Icon,
  Popover,
  PopoverTrigger,
  PopoverContent,
  useBreakpointValue,
  useDisclosure,
} from '@chakra-ui/react';
import {
  HamburgerIcon,
  CloseIcon,
  ChevronDownIcon,
  ChevronRightIcon,
} from '@chakra-ui/icons';

export function Logo() {
  const titleGradient = useColorModeValue('linear(to-b, #A6C7FF, #90B3FF, #5D74A5, #5D74A5)', 'linear(to-b, #5D729F, #3B4968, #1A202C)')

  return (
      <Center height="80px">
      <Link ml="30px" mr="20px"
        bgGradient={titleGradient}
        bgClip='text'
        fontSize={{ base: '4xl', md: '5xl' }}
        fontWeight='extrabold'
        textAlign={{ base: 'center', md: 'center' }}
        href="/home"
      >
        Hockey Reply
      </Link>
      <Badge variant='outline' colorScheme="gray" mt="8px">BETA</Badge>
      </Center>
    )
}


export const Header = props => {
  const { isOpen, onToggle } = useDisclosure();
  const linkColor = useColorModeValue('blue.400', 'blue.300');
  const linkHoverColor = useColorModeValue('blue.600', 'blue.100');

  return (
    <Box>
      <Flex
        bg={useColorModeValue('white', 'gray.800')}
        color={useColorModeValue('gray.600', 'white')}
        minH={'60px'}
        py={{ base: 2 }}
        px={{ base: 4 }}
        borderBottom={1}
        borderStyle={'solid'}
        borderColor={useColorModeValue('gray.200', 'gray.900')}
        align={'center'}>
        <Box
          ml={{ base: -2 }}
          display={{ base: 'flex', md: 'none' }}>
          <IconButton
            onClick={onToggle}
            icon={
              isOpen ? <CloseIcon w={3} h={3} /> : <HamburgerIcon w={5} h={5} />
            }
            variant={'ghost'}
            aria-label={'Toggle Navigation'}
          />
        </Box>
        <Flex flex={{ base: 1 }} justify={{ base: 'center', md: 'start' }}>
          <Logo></Logo>
        </Flex>
        <DesktopNav signed_in={props.signed_in} react_navigate={props.react_navigate}/>
      </Flex>

      <Collapse in={isOpen} animateOpacity>
        <MobileNav signed_in={props.signed_in} react_navigate={props.react_navigate}/>
      </Collapse>
    </Box>
  );
}

const DesktopNav = props => {
  const linkColor = useColorModeValue('blue.400', 'blue.300');
  const linkHoverColor = useColorModeValue('blue.600', 'blue.100');
  const popoverContentBgColor = useColorModeValue('gray.50', 'gray.700');

  return (
    <Stack direction={'row'} spacing={4} display={{ base: 'none', md: 'flex' }}>
      {NAV_ITEMS.map((navItem) => (
        <Box key={navItem.label}>
          <Popover trigger={'hover'} placement={'bottom'}>
              <Center height="80px">
            <PopoverTrigger>
                <Link
                  p={2}
                  href={navItem.href ?? '#'}
                  fontSize={'sm'}
                  fontWeight={500}
                  color={linkColor}
                  _hover={{
                    textDecoration: 'none',
                    color: linkHoverColor,
                  }}>
                  {navItem.label}
                </Link>
            </PopoverTrigger>

            {navItem.children && (
              <PopoverContent
                border={0}
                boxShadow={'xl'}
                bg={popoverContentBgColor}
                p={4}
                rounded={'xl'}
                minW={'sm'}>
                <Stack>
                  {navItem.children.map((child) => (
                    <DesktopSubNav key={child.label} {...child} />
                  ))}
                </Stack>
              </PopoverContent>
            )}
            </Center>
          </Popover>
        </Box>
      ))}
          { props.signed_in &&
          <Button
            as={'a'}
            fontSize={'sm'}
            fontWeight={500}
            variant={'link'}
            color={linkColor}
            href={'/sign-out'}
            _hover={{
                    textDecoration: 'none',
                    color: linkHoverColor,
                  }}>
            Sign Out
          </Button>
          }
          { !props.signed_in &&
          <Button
            as={'a'}
            fontSize={'sm'}
            fontWeight={500}
            variant={'link'}
            href={'/sign-in'}
            color={linkColor}
            _hover={{
                    textDecoration: 'none',
                    color: linkHoverColor,
                  }}>
            Sign In
          </Button>
          }
    </Stack>
  );
};

const DesktopSubNav = ({ label, href, subLabel }: NavItem) => {
  return (
    <Link
      href={href}
      role={'group'}
      display={'block'}
      p={2}
      rounded={'md'}
      _hover={{ bg: useColorModeValue('blue.50', 'gray.900') }}>
      <Stack direction={'row'} align={'center'}>
        <Box>
          <Text
            transition={'all .3s ease'}
            _groupHover={{ color: 'blue.500' }}
            fontWeight={500}>
            {label}
          </Text>
          <Text fontSize={'sm'}>{subLabel}</Text>
        </Box>
        <Flex
          transition={'all .3s ease'}
          transform={'translateX(-10px)'}
          opacity={0}
          _groupHover={{ opacity: '100%', transform: 'translateX(0)' }}
          justify={'flex-end'}
          align={'center'}
          flex={1}>
          <Icon color={'blue.400'} w={5} h={5} as={ChevronRightIcon} />
        </Flex>
      </Stack>
    </Link>
  );
};

const MobileNav = props => {
  return (
    <Stack
      bg={useColorModeValue('white', 'gray.800')}
      p={4}
      display={{ md: 'none' }}>
      {NAV_ITEMS.map((navItem) => (
        <MobileNavItem key={navItem.label} {...navItem} />
      ))}
      { !props.signed_in &&
        <MobileNavItem key='sign-in-mobile-nav' label='Sign In' href='/sign-in' />
      }
      { props.signed_in &&
        <MobileNavItem key='sign-out-mobile-nav' label='Sign Out' href='/sign-out' />
      }
    </Stack>
  );
};

const MobileNavItem = ({ label, children, href }: NavItem) => {
  const { isOpen, onToggle } = useDisclosure();

  return (
    <Stack spacing={4} onClick={children && onToggle}>
      <Flex
        py={2}
        as={Link}
        href={href ?? '#'}
        justify={'space-between'}
        align={'center'}
        _hover={{
          textDecoration: 'none',
        }}>
        <Text
          fontWeight={600}
          color={useColorModeValue('gray.600', 'gray.200')}>
          {label}
        </Text>
        {children && (
          <Icon
            as={ChevronDownIcon}
            transition={'all .25s ease-in-out'}
            transform={isOpen ? 'rotate(180deg)' : ''}
            w={6}
            h={6}
          />
        )}
      </Flex>

      <Collapse in={isOpen} animateOpacity style={{ marginTop: '0!important' }}>
        <Stack
          mt={2}
          pl={4}
          borderLeft={1}
          borderStyle={'solid'}
          borderColor={useColorModeValue('gray.200', 'gray.700')}
          align={'start'}>
          {children &&
            children.map((child) => (
              <Link key={child.label} py={2} href={child.href}>
                {child.label}
              </Link>
            ))}
        </Stack>
      </Collapse>
    </Stack>
  );
};

interface NavItem {
  label: string;
  subLabel?: string;
  children?: Array<NavItem>;
  href?: string;
}

const NAV_ITEMS: Array<NavItem> = [
  {
    label: 'Home',
    href: '/home',
  },
  {
    label: 'Schedule',
    children: [
      {
        label: 'San Jose',
        href: 'https://stats.sharksice.timetoscore.com/display-stats.php?league=1',
      },
      {
        label: 'Fremont',
        href: 'https://stats.sharksice.timetoscore.com/display-stats.php?league=15',
      },
    ],
  },
];
