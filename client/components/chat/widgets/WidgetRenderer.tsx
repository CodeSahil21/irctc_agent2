"use client";

import type { ChatWidget } from "@/types/chat";
import { DatePickerWidgetCard } from "./DatePickerWidget";
import { StationPickerWidgetCard } from "./StationPickerWidget";
import { ClassSelectorWidgetCard } from "./ClassSelectorWidget";
import { PassengerCountWidgetCard } from "./PassengerCountWidget";
import { QuickReplyWidgetCard } from "./QuickReplyWidget";

interface Props {
  widget: ChatWidget;
  onSubmit: (value: string) => void;
  submitted: boolean;
}

export function WidgetRenderer({ widget, onSubmit, submitted }: Props) {
  switch (widget.type) {
    case "date_picker":
      return <DatePickerWidgetCard widget={widget} onSubmit={onSubmit} submitted={submitted} />;
    case "station_picker":
      return <StationPickerWidgetCard widget={widget} onSubmit={onSubmit} submitted={submitted} />;
    case "class_selector":
      return <ClassSelectorWidgetCard widget={widget} onSubmit={onSubmit} submitted={submitted} />;
    case "passenger_count":
      return <PassengerCountWidgetCard widget={widget} onSubmit={onSubmit} submitted={submitted} />;
    case "quick_reply":
      return <QuickReplyWidgetCard widget={widget} onSubmit={onSubmit} submitted={submitted} />;
  }
}
