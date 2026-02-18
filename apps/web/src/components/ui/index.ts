/**
 * UI Components Barrel Export
 * CelesteOS Design System
 *
 * Usage:
 * import { StatusPill, Toast, PrimaryButton } from '@/components/ui';
 */

// Base UI Components (Design System)
export { StatusPill, type StatusPillProps } from './StatusPill';
export { VitalSignsRow, type VitalSign, type VitalSignsRowProps } from './VitalSignsRow';
export { SectionContainer, type SectionContainerProps } from './SectionContainer';
export { GhostButton, type GhostButtonProps } from './GhostButton';
export { PrimaryButton, type PrimaryButtonProps } from './PrimaryButton';
export { EntityLink, type EntityLinkProps } from './EntityLink';
export { Toast, type ToastProps } from './Toast';

// Existing shadcn/ui Components
export { Button, buttonVariants, type ButtonProps } from './button';
export { Checkbox } from './checkbox';
export { Input } from './input';
export { Label } from './label';
export { Textarea } from './textarea';
export {
  Select,
  SelectContent,
  SelectGroup,
  SelectItem,
  SelectLabel,
  SelectSeparator,
  SelectTrigger,
  SelectValue,
} from './select';
export {
  Dialog,
  DialogClose,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogOverlay,
  DialogPortal,
  DialogTitle,
  DialogTrigger,
} from './dialog';
export {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogOverlay,
  AlertDialogPortal,
  AlertDialogTitle,
  AlertDialogTrigger,
} from './alert-dialog';
export {
  DropdownMenu,
  DropdownMenuCheckboxItem,
  DropdownMenuContent,
  DropdownMenuGroup,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuPortal,
  DropdownMenuRadioGroup,
  DropdownMenuRadioItem,
  DropdownMenuSeparator,
  DropdownMenuShortcut,
  DropdownMenuSub,
  DropdownMenuSubContent,
  DropdownMenuSubTrigger,
  DropdownMenuTrigger,
} from './dropdown-menu';

// Utility Components
export { Pagination } from './Pagination';
export { SortControls } from './SortControls';
