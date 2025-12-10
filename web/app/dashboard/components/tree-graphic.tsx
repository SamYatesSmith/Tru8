import Image from 'next/image';

export function TreeGraphic() {
  return (
    <div className="w-64 h-64 relative">
      <Image
        src="/imagery/choice.tree.png"
        alt="Decision tree"
        fill
        sizes="256px"
        loading="eager"
        className="object-contain"
      />
    </div>
  );
}
