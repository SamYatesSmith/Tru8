import Image from 'next/image';

export function CompassGraphic() {
  return (
    <div className="w-64 h-64 relative">
      <Image
        src="/imagery/history.compass.png"
        alt="Compass"
        fill
        className="object-contain"
      />
    </div>
  );
}
