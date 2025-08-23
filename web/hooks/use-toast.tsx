import { useState } from "react";

export interface Toast {
  id: string;
  title?: string;
  description?: string;
  variant?: "default" | "destructive";
  action?: React.ReactNode;
}

const TOAST_LIMIT = 3;
const TOAST_REMOVE_DELAY = 1000000;

let count = 0;

function genId() {
  count = (count + 1) % Number.MAX_VALUE;
  return count.toString();
}

type ToasterToast = Toast & {
  id: string;
  title?: string;
  description?: string;
  action?: React.ReactNode;
};

const actionTypes = {
  ADD_TOAST: "ADD_TOAST",
  UPDATE_TOAST: "UPDATE_TOAST", 
  DISMISS_TOAST: "DISMISS_TOAST",
  REMOVE_TOAST: "REMOVE_TOAST",
} as const;

let memoryState: { toasts: ToasterToast[] } = { toasts: [] };
let listeners: Array<(state: typeof memoryState) => void> = [];

const dispatch = (action: any) => {
  switch (action.type) {
    case "ADD_TOAST":
      memoryState.toasts = [action.toast, ...memoryState.toasts].slice(
        0,
        TOAST_LIMIT
      );
      break;
    case "UPDATE_TOAST":
      memoryState.toasts = memoryState.toasts.map((t) =>
        t.id === action.toast.id ? { ...t, ...action.toast } : t
      );
      break;
    case "DISMISS_TOAST": {
      const { toastId } = action;
      if (toastId) {
        memoryState.toasts = memoryState.toasts.filter((t) => t.id !== toastId);
      } else {
        memoryState.toasts = [];
      }
      break;
    }
    case "REMOVE_TOAST":
      memoryState.toasts = memoryState.toasts.filter((t) => t.id !== action.toastId);
      break;
  }
  listeners.forEach((listener) => {
    listener(memoryState);
  });
};

function toast({ ...props }: Omit<ToasterToast, "id">) {
  const id = genId();
  const update = (props: ToasterToast) =>
    dispatch({
      type: "UPDATE_TOAST",
      toast: { ...props, id },
    });
  
  const dismiss = () => dispatch({ type: "DISMISS_TOAST", toastId: id });

  dispatch({
    type: "ADD_TOAST", 
    toast: {
      ...props,
      id,
      open: true,
      onOpenChange: (open: boolean) => {
        if (!open) dismiss();
      },
    },
  });

  return {
    id: id,
    dismiss,
    update,
  };
}

function useToast() {
  const [state, setState] = useState<typeof memoryState>(memoryState);

  React.useEffect(() => {
    listeners.push(setState);
    return () => {
      const index = listeners.indexOf(setState);
      if (index > -1) {
        listeners.splice(index, 1);
      }
    };
  }, [state]);

  return {
    ...state,
    toast,
    dismiss: (toastId?: string) => dispatch({ type: "DISMISS_TOAST", toastId }),
  };
}

export { useToast, toast };